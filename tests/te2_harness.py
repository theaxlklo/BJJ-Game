"""Test harness for TE-2 route-step exactness (not a test module).

Observes real batch matches and, at every real engine step, checks:
- full-state load: a fresh sandbox loaded with the route branch has exactly
  the real match's complete mutable state (every init=False MountMatch field
  except the history log);
- successor agreement: the route step from the pre-step route branch gives
  exactly the real post-step route branch (attempt: the realized case exactly,
  and inside the exact support; reset_window; recovery_hold; the window loop).

Synthetic fixtures only (seeds >= 910000)."""
from __future__ import annotations

from contextlib import ExitStack
import dataclasses
from enum import Enum
from unittest import mock

from bjj_game.engine.match import MountMatch
from bjj_game.interfaces import batch as batch_module
from bjj_game.interfaces import tactical_projection_v2 as v2
from bjj_game.interfaces import tactical_route as route
from bjj_game.interfaces.batch import BatchInitiatorPolicy, run_batch
from bjj_game.interfaces.handoff_policy import D3BTokenLockoutController

MUTABLE_FIELDS = tuple(f.name for f in dataclasses.fields(MountMatch)
                       if not f.init and f.name != "history")


def snapshot(obj):
    if isinstance(obj, Enum) or obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {repr(k): snapshot(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [snapshot(x) for x in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(repr(x) for x in obj)
    if dataclasses.is_dataclass(obj):
        return {f.name: snapshot(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    slots = [s for cls in type(obj).__mro__ for s in getattr(cls, "__slots__", ())
             if s not in ("__dict__", "__weakref__")]
    if slots or hasattr(obj, "__dict__"):
        out = {s: snapshot(getattr(obj, s)) for s in slots if hasattr(obj, s)}
        out.update({k: snapshot(v) for k, v in getattr(obj, "__dict__", {}).items()})
        return out
    raise TypeError(f"snapshot cannot read {type(obj).__name__}")


def mutable_state(match: MountMatch) -> dict:
    return {name: snapshot(getattr(match, name)) for name in MUTABLE_FIELDS}


def _post(match, controller):
    if match.submission_tapped:
        return v2.TAP
    if match.exit_destination is not None:
        return v2.EXIT
    if match.clock_seconds <= 0:
        return v2.TIMEOUT
    return route.route_branch_of(match, controller)


def observe_steps(kwargs: dict, policy: BatchInitiatorPolicy, *, check_support=True):
    """Run one batch; return (BatchRun, events, failures)."""
    context = v2.Context.from_batch_kwargs(
        {**kwargs, "initiator_policy": BatchInitiatorPolicy.TACTICAL_V1})
    real: dict = {}
    controllers: dict = {}
    models: dict = {}
    pending_loop: dict = {}
    events: list = []
    failures: list = []
    originals = {n: getattr(MountMatch, n)
                 for n in ("attempt", "reset_window", "recovery_hold",
                           "consume_free_initiative_window")}
    original_decide = D3BTokenLockoutController.decide
    original_controller_for = batch_module.handoff_controller_for

    def factory(*a, **k):
        m = MountMatch(*a, **k)
        real[id(m)] = m
        return m

    def controller_for(mode, match):
        c = original_controller_for(mode, match)
        controllers[id(match)] = c
        return c

    def model_for(match):
        if id(match) not in models:
            models[id(match)] = route.RouteModel(
                match, context, budget=route.RouteBudget(rss_bytes=None))
        return models[id(match)]

    def check_load(match, rb, where):
        sandbox = route.RouteSandbox(match).load(rb)
        if mutable_state(sandbox) != mutable_state(match):
            diff = [n for n in MUTABLE_FIELDS
                    if snapshot(getattr(sandbox, n)) != snapshot(getattr(match, n))]
            failures.append(("load", where, diff))

    def close_loop(match):
        pre = pending_loop.pop(id(match), None)
        if pre is None:
            return
        post = route.route_branch_of(match, controllers.get(id(match)))
        got = model_for(match).window_loop(pre)
        events.append(("loop", pre.stall is not None and pre.stall[6]))
        if got != post:
            failures.append(("loop", pre, got, post))

    def wrap(name):
        def wrapped(match, *a, **kw):
            if id(match) not in real:
                return originals[name](match, *a, **kw)
            controller = controllers.get(id(match))
            if name == "consume_free_initiative_window":
                pre = route.route_branch_of(match, controller)
                check_load(match, pre, "loop")
                pending_loop[id(match)] = pre
                return originals[name](match, *a, **kw)
            close_loop(match)
            pre = route.route_branch_of(match, controller)
            check_load(match, pre, name)
            result = originals[name](match, *a, **kw)
            post = _post(match, controller)
            model = model_for(match)
            if name == "attempt":
                m = model.steps.load(pre)
                m.attempt(**kw)
                exact = model.steps.read(v2.Sandbox.controller(pre.branch.d3b))
                if exact != post:
                    failures.append(("attempt-exact", pre, kw["action_id"], exact, post))
                if check_support:
                    support = dict(model.exchange(pre, kw["action_id"], kw["commitment"]))
                    if post not in support:
                        failures.append(("attempt-support", pre, kw["action_id"]))
            elif name == "reset_window":
                got = model.reset(pre)[0][0]
                if got != post:
                    failures.append(("reset", pre, got, post))
            else:
                m = model.steps.load(pre)
                m.recovery_hold()
                got = model.steps.read(v2.Sandbox.controller(pre.branch.d3b))
                if got != post:
                    failures.append(("hold", pre, got, post))
            events.append((name, pre.stall is not None))
            return result
        return wrapped

    def decide(controller, match, *, armed):
        if id(match) in real:
            close_loop(match)
        return original_decide(controller, match, armed=armed)

    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(batch_module, "MountMatch", factory))
        stack.enter_context(mock.patch.object(batch_module, "handoff_controller_for",
                                              controller_for))
        stack.enter_context(mock.patch.object(D3BTokenLockoutController, "decide", decide))
        for name in originals:
            stack.enter_context(mock.patch.object(MountMatch, name, wrap(name)))
        result = run_batch(initiator_policy=policy, **kwargs)
    return result, events, failures

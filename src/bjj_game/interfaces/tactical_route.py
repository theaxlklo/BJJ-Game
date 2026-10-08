"""TE-2 exact route value (docs/TACTICAL_EVALUATOR_TE2_PREREGISTRATION.md,
binding at 218f1c0ab94d6999abd06157876f48704e8ba6e1, section 4).

Q(s, o) is the exact value of choosing option o first at a Top window, then
optimal Top play: max over Top options (RESET and every candidate), exact
expectation over chance (v2.exchange_cases) and over the O-3 TE-1 opponent's
deterministic decision, with Fraction weights. Success is a Threat entry or
a Tap. The horizon is QB-quiescent: base B = 5 and bound M = 13 decision
windows, both counted from the decision being made.

Every transition runs the engine's own method on a fresh sandbox loaded with
the full route branch (section 4.1): attempt() per chance case,
reset_window() for every RESET, recovery_hold() for D3-B LOCKOUT_HOLD, and the
batch's window loop (a pending free-initiative window first; otherwise
behavior choice, advance(), D3-B observation, re-choice). The route branch is
projection v2's Branch plus every stalling field the engine reads or writes
under v0.3b. With stalling off those fields are absent and the search equals
the 3b08cea characterization instrument exactly (pinned by tests).

There is no sampling, pruning, beam, averaging or depth reduction. A budget
overflow raises RouteBudgetExceeded: the run is OPEN, never approximated.
Pure: no RNG, no mutation of the live match or the live D3-B controller.
Projection v2 is used, never modified.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from fractions import Fraction
import os
import sys

from ..domain.action import Commitment
from ..domain.model import Side
from ..engine.match import MountMatch
from ..positions.mount.catalog import TOP_AMERICANA_ARM_ISOLATION
from . import tactical_evaluator as te
from . import tactical_projection_v2 as v2
from .handoff_policy import HandoffDecisionKind

PREREGISTRATION = "218f1c0ab94d6999abd06157876f48704e8ba6e1"
BASE_WINDOWS = 5
BOUND_WINDOWS = 13
TARGET = TOP_AMERICANA_ARM_ISOLATION
RESET = ("RESET", None)

DECISION_NODE_LIMIT = 3_000_000
MATCH_MEMO_LIMIT = 20_000_000
RSS_LIMIT_BYTES = 16 * 1024 ** 3
RSS_CHECK_EVERY = 4096


class RouteBudgetExceeded(RuntimeError):
    """A frozen budget was exceeded: the run is OPEN (never approximated)."""

    def __init__(self, which: str, detail: str = "") -> None:
        super().__init__(f"route budget exceeded: {which} {detail}".strip())
        self.which = which


@dataclass(frozen=True, slots=True)
class RouteBudget:
    decision_nodes: int = DECISION_NODE_LIMIT
    match_memo: int = MATCH_MEMO_LIMIT
    rss_bytes: int | None = RSS_LIMIT_BYTES


# ---------------------------------------------------------------------------
# Resident memory (the T8 RSS cap)
# ---------------------------------------------------------------------------


def rss_bytes() -> int | None:
    """Current resident set size of this process, or None if unmeasurable."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class _Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            counters = _Counters()
            counters.cb = ctypes.sizeof(_Counters)
            kernel = ctypes.WinDLL("kernel32")
            psapi = ctypes.WinDLL("psapi")
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
                                                   ctypes.POINTER(_Counters), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            ok = psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                            ctypes.byref(counters), counters.cb)
            return int(counters.WorkingSetSize) if ok else None
        with open("/proc/self/statm", encoding="ascii") as handle:
            return int(handle.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, AttributeError):
        return None


@contextmanager
def exclusive_measurement(lock_path) -> object:
    """T8: one TACTICAL_V2 surface process at a time. Raises if the lock is
    already held (never waits, never runs concurrently)."""
    path = os.fspath(lock_path)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError(f"another TACTICAL_V2 measurement holds {path}") from None
    try:
        os.write(fd, str(os.getpid()).encode())
        yield path
    finally:
        os.close(fd)
        os.remove(path)


# ---------------------------------------------------------------------------
# Route branch (section 4.1)
# ---------------------------------------------------------------------------

Stall = tuple  # (top clock, bottom clock, top warned, bottom warned,
#                 top offenses, bottom offenses, free pending, free beneficiary)


@dataclass(frozen=True, slots=True)
class RouteBranch:
    branch: v2.Branch
    stall: Stall | None        # None exactly when v0.3b stalling is off

    @property
    def state(self) -> te.State:
        return self.branch.state


def stall_of(match: MountMatch) -> Stall | None:
    if not match.enable_v03b_stalling:
        return None
    t = match.stalling_tracker
    return (t.clocks[Side.TOP], t.clocks[Side.BOTTOM], t.warned[Side.TOP],
            t.warned[Side.BOTTOM], t.offenses[Side.TOP], t.offenses[Side.BOTTOM],
            match.free_initiative_pending, match.free_initiative_beneficiary)


def route_branch_of(match: MountMatch, controller) -> RouteBranch:
    return RouteBranch(v2.branch_of(match, controller), stall_of(match))


class RouteSandbox:
    """A fresh MountMatch with the live configuration, loaded with a full
    route branch (never the live match)."""

    def __init__(self, template: MountMatch) -> None:
        self.inner = v2.Sandbox(template)
        self.match = self.inner.match
        self.stalling = self.match.enable_v03b_stalling

    def load(self, rb: RouteBranch) -> MountMatch:
        m = self.inner.load(rb.branch)
        if (rb.stall is None) == self.stalling:
            raise RuntimeError("route branch stalling fields do not match the configuration")
        if rb.stall is not None:
            tc, bc, tw, bw, to, bo, pending, beneficiary = rb.stall
            t = m.stalling_tracker
            t.clocks = {Side.TOP: tc, Side.BOTTOM: bc}
            t.warned = {Side.TOP: tw, Side.BOTTOM: bw}
            t.offenses = {Side.TOP: to, Side.BOTTOM: bo}
            m.free_initiative_pending = pending
            m.free_initiative_beneficiary = beneficiary
        return m

    def read(self, controller) -> RouteBranch | str:
        result = self.inner.read(controller)
        if isinstance(result, str):
            return result
        return RouteBranch(result, stall_of(self.match))


def success(state: te.State) -> bool:
    return state.stage is not None


# ---------------------------------------------------------------------------
# Route model: exact steps, the opponent contract and the solver
# ---------------------------------------------------------------------------


class RouteModel:
    """Exact route values for one live match. `context` is the O-3 contract
    (a TACTICAL_V1 projection-v2 Context). Step caches and the memo are keyed
    by the full route branch and are exact; clear by creating a new model per
    match."""

    def __init__(self, live: MountMatch, context: v2.Context, *,
                 budget: RouteBudget = RouteBudget()) -> None:
        self.context = context
        self.budget = budget
        self.steps = RouteSandbox(live)
        self.queries = RouteSandbox(live)
        self.opponent_contract = v2.Continuation(v2.Sandbox(live).match, context)
        self._exchange: dict = {}
        self._reset: dict = {}
        self._loop: dict = {}
        self._opponent: dict = {}
        self._options: dict = {}
        self._unresolved: dict = {}
        self.memo: dict = {}
        self.decision_nodes = 0
        self.decisions = 0
        self.searches_by_side = {Side.TOP: 0, Side.BOTTOM: 0}

    # -- steps -----------------------------------------------------------------

    def exchange(self, rb: RouteBranch, action_id: str, requested: Commitment):
        """((RouteBranch-or-label, weight), ...) after attempt(), per exact case."""
        key = (rb, action_id, requested)
        cached = self._exchange.get(key)
        if cached is None:
            out: dict = {}
            controller = v2.Sandbox.controller(rb.branch.d3b)
            cases = v2.exchange_cases(self.steps.match, self.context.model, rb.state,
                                      action_id, requested)
            for weight, read, response_c, response_id in cases:
                m = self.steps.load(rb)
                m.attempt(action_id=action_id, response_id=response_id, commitment=requested,
                          response_commitment=response_c, recognition_read=read)
                after = self.steps.read(controller)
                out[after] = out.get(after, Fraction(0)) + weight
            cached = self._exchange[key] = tuple(out.items())
        return cached

    def reset(self, rb: RouteBranch):
        """The engine's own reset_window(), including v0.3b stalling."""
        cached = self._reset.get(rb)
        if cached is None:
            m = self.steps.load(rb)
            m.reset_window()
            cached = self._reset[rb] = ((self.steps.read(v2.Sandbox.controller(rb.branch.d3b)),
                                         Fraction(1)),)
        return cached

    def window_loop(self, rb: RouteBranch) -> RouteBranch | str:
        """The batch's loop between windows (run_batch at fd19dd0)."""
        if rb in self._loop:
            return self._loop[rb]
        m = self.steps.load(rb)
        controller = v2.Sandbox.controller(rb.branch.d3b)
        if m.enable_v03b_stalling and m.consume_free_initiative_window() is not None:
            result = self.steps.read(controller)        # free window: no advance
        else:
            top = self.context.top_policy.choose(m)
            bottom = self.context.bottom_policy.choose(m)
            if controller is not None:
                bottom = controller.pre_advance_bottom_behavior(bottom)
            m.set_behaviors(top=top, bottom=bottom)
            m.advance()
            if controller is not None:
                controller.observe_advance(m)
            if not m.ended:
                m.set_behaviors(top=self.context.top_policy.choose(m),
                                bottom=self.context.bottom_policy.choose(m))
            result = self.steps.read(controller)
        self._loop[rb] = result
        return result

    def opponent(self, rb: RouteBranch):
        """Bottom window: the O-3 TE-1 decision, then the exact transition."""
        if rb in self._opponent:
            return self._opponent[rb]
        kind, action_id, requested, controller = self.opponent_contract.opponent_decision(rb.branch)
        fields = v2.controller_fields(controller)
        decided = RouteBranch(replace(rb.branch, d3b=fields), rb.stall)
        if kind is HandoffDecisionKind.LOCKOUT_HOLD:
            m = self.steps.load(decided)
            m.recovery_hold()
            result = ((self.steps.read(v2.Sandbox.controller(fields)), Fraction(1)),)
        elif action_id is None:
            result = self.reset(decided)
        else:
            result = self.exchange(decided, action_id, requested)
        self._opponent[rb] = result
        return result

    # -- options and QB --------------------------------------------------------

    def options(self, rb: RouteBranch, allowed=te.COMMITMENTS) -> tuple:
        key = (rb.state, allowed)
        if key in self._options:
            return self._options[key]
        m = self.queries.load(rb)
        pool = rb.state.top.current
        out = [RESET]
        for action_id in m.legal_action_ids(Side.TOP):
            seen = set()
            for c in allowed:
                effective = te.funded(m, c, pool)
                if effective in seen:
                    continue
                seen.add(effective)
                out.append((action_id, c))
        self._options[key] = tuple(out)
        return self._options[key]

    def unresolved(self, rb: RouteBranch) -> bool:
        """QB (section 4, frozen exactly)."""
        s = rb.state
        if s in self._unresolved:
            return self._unresolved[s]
        result = TARGET in s.ready or s.tier(TARGET) > 0 or s.bottom.latched
        if not result and s.initiator is Side.TOP:
            m = self.queries.load(rb)
            for action_id in m.legal_action_ids(Side.TOP):
                for c in te.COMMITMENTS:
                    if te.funded(m, c, s.top.current) is not c:
                        continue
                    v = te.evaluate(m, self.context.model, s, action_id, c, project=False)
                    if v.terminal > 0 or v.progress > 0:
                        result = True
                        break
                if result:
                    break
        self._unresolved[s] = result
        return result

    # -- transitions -----------------------------------------------------------

    def transitions(self, rb: RouteBranch, option) -> tuple:
        """((weight, next-decision RouteBranch or terminal label), ...)."""
        if rb.state.initiator is Side.TOP:
            items = self.reset(rb) if option == RESET else self.exchange(rb, *option)
        else:
            items = self.opponent(rb)
        out = []
        for item, w in items:
            if isinstance(item, str):
                out.append((w, item))
            elif success(item.state):
                out.append((w, v2.TAP))           # success before the loop
            else:
                out.append((w, self.window_loop(item)))
        return tuple(out)

    # -- solver ----------------------------------------------------------------

    def _charge(self) -> None:
        self.decision_nodes += 1
        if self.decision_nodes > self.budget.decision_nodes:
            raise RouteBudgetExceeded("decision_nodes", str(self.budget.decision_nodes))
        if len(self.memo) >= self.budget.match_memo:
            raise RouteBudgetExceeded("match_memo", str(self.budget.match_memo))
        if self.decision_nodes % RSS_CHECK_EVERY == 0:
            self._check_rss()

    def _check_rss(self) -> None:
        if self.budget.rss_bytes is None:
            return
        rss = rss_bytes()
        if rss is None:
            raise RouteBudgetExceeded("rss", "unmeasurable on this platform")
        if rss > self.budget.rss_bytes:
            raise RouteBudgetExceeded("rss", f"{rss} > {self.budget.rss_bytes}")

    def value(self, rb: RouteBranch, depth: int) -> Fraction:
        if success(rb.state):
            return Fraction(1)
        if depth >= BOUND_WINDOWS:
            return Fraction(0)
        if depth >= BASE_WINDOWS and not self.unresolved(rb):
            return Fraction(0)
        key = (rb, depth)
        cached = self.memo.get(key)
        if cached is not None:
            return cached
        self._charge()
        if rb.state.initiator is Side.TOP:
            best = max(self.q(rb, o, depth) for o in self.options(rb))
        else:
            best = self._expect(self.transitions(rb, None), depth)
        self.memo[key] = best
        return best

    def _expect(self, transitions, depth: int) -> Fraction:
        total = Fraction(0)
        for w, item in transitions:
            if isinstance(item, str):
                total += w * (1 if item == v2.TAP else 0)
            elif success(item.state):
                total += w
            else:
                total += w * self.value(item, depth + 1)
        return total

    def q(self, rb: RouteBranch, option, depth: int = 0) -> Fraction:
        return self._expect(self.transitions(rb, option), depth)

    def root_values(self, rb: RouteBranch, allowed=te.COMMITMENTS) -> dict:
        """Q(s, o) for every option at a real Top decision (one decision)."""
        if rb.state.initiator is not Side.TOP:
            self.searches_by_side[Side.BOTTOM] += 1
            raise RuntimeError("TE-2 route search started from a Bottom window")
        self.searches_by_side[Side.TOP] += 1
        self.decision_nodes = 0
        self.decisions += 1
        self._check_rss()
        return {o: self.q(rb, o, 0) for o in self.options(rb, allowed)}

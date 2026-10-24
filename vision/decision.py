from collections import deque, Counter


class Decision:
    """
    Turns noisy perception into one stable command for the legs.

    - smoothing: center proximity is averaged over a window, and the direction
      is chosen by majority vote over the window (does not twitch on a single frame)
    - hysteresis: two thresholds (block_on/block_off) so that "blocked/clear"
      does not flicker back and forth
    - watchdog: if there is no fresh data for longer than stale_timeout — command STOP

    Commands: FORWARD, TURN_LEFT, TURN_RIGHT, STOP
    """

    def __init__(self, window=8, block_on=0.6, block_off=0.45, stale_timeout=0.5):
        self.center_hist = deque(maxlen=window)
        self.dir_hist = deque(maxlen=window)

        self.blocked = False          # hysteresis state
        self.command = "STOP"
        self.direction = "CENTER"

        self.block_on = block_on
        self.block_off = block_off
        self.stale_timeout = stale_timeout

    def update(self, nav_result, data_age):

        # --- WATCHDOG: no fresh data -> STOP ---
        if data_age is None or data_age > self.stale_timeout:
            self.command = "STOP"
            return self._out("STALE", None, data_age)

        if nav_result is None:
            self.command = "STOP"
            return self._out("NO_DATA", None, data_age)

        scores = nav_result["scores"]
        names = nav_result["names"]
        center_idx = len(scores) // 2

        # --- smooth center proximity ---
        self.center_hist.append(scores[center_idx])
        center_avg = sum(self.center_hist) / len(self.center_hist)

        # --- hysteresis on "blocked" ---
        if not self.blocked and center_avg > self.block_on:
            self.blocked = True
        elif self.blocked and center_avg < self.block_off:
            self.blocked = False

        # --- smooth direction by majority vote over the window ---
        self.dir_hist.append(nav_result["clear_idx"])
        voted_idx = Counter(self.dir_hist).most_common(1)[0][0]
        self.direction = names[voted_idx]

        # --- command ---
        if not self.blocked:
            self.command = "FORWARD"
        else:
            if voted_idx < center_idx:
                self.command = "TURN_LEFT"
            elif voted_idx > center_idx:
                self.command = "TURN_RIGHT"
            else:
                # center is blocked, but the clearest sector is also the center -> boxed in
                self.command = "STOP"

        return self._out("OK", center_avg, data_age)

    def _out(self, reason, center_avg, data_age):
        return {
            "command": self.command,
            "direction": self.direction,
            "blocked": self.blocked,
            "reason": reason,
            "center_avg": center_avg,
            "data_age": data_age,
        }
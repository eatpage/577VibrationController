"""自检脚本：不依赖手柄，验证波形库与引擎的基本正确性。

用法： python selftest.py
"""

from __future__ import annotations

import sys
import time

from core import xinput_backend
from core.rumble_engine import RumbleEngine
from core.waveforms import WAVEFORMS, eval_curve, waveforms_by_category

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  [ok]   {msg}")
    else:
        print(f"  [FAIL] {msg}")
        failures.append(msg)


print("=" * 68)
print("1. 波形库自检")
print("=" * 68)

check(len(WAVEFORMS) >= 30, f"波形数量 = {len(WAVEFORMS)}（要求 >= 30）")

N = 2000
for key, wf in sorted(WAVEFORMS.items()):
    lo, hi = 1.0, 0.0
    for i in range(N):
        p = i / N
        l, r = wf.sample(p)
        if not (0.0 <= l <= 1.0) or not (0.0 <= r <= 1.0):
            failures.append(f"{key} 输出越界: l={l} r={r} @p={p}")
            break
        lo = min(lo, l, r)
        hi = max(hi, l, r)
    else:
        # 循环连续性：f(1-eps) 与 f(0) 应接近
        ln, rn = wf.sample(1.0 - 1e-6)
        l0, r0 = wf.sample(0.0)
        gap = max(abs(ln - l0), abs(rn - r0))
        # 跨越不连续的波形（阶梯/锯齿/敲击等）允许较大跳变，但不应超过 1.0
        if gap > 1.0:
            failures.append(f"{key} 循环接缝异常 gap={gap:.3f}")
        if hi - lo < 0.05 and key not in ("steady",):
            failures.append(f"{key} 几乎无变化（动态范围 {hi - lo:.3f}）")
        print(f"  [ok]   {key:<11} {wf.name:<6} 动态范围 {lo:.2f}~{hi:.2f}  峰值 {hi:.2f}")

print()
print("2. 自定义曲线插值自检")
pts = [(0.0, 0.0), (0.5, 1.0)]
check(abs(eval_curve(pts, 0.0) - 0.0) < 1e-6, "曲线起点 = 0")
check(abs(eval_curve(pts, 0.5) - 1.0) < 1e-6, "曲线中点 = 1")
check(abs(eval_curve(pts, 0.25) - 0.5) < 1e-6, "曲线 1/4 处 = 0.5")
check(abs(eval_curve(pts, 0.75) - 0.5) < 1e-6, "曲线 3/4 处 = 0.5（回程插值）")
check(abs(eval_curve(pts, 0.999) - 0.002) < 0.01, "曲线接近闭合")
check(eval_curve([], 0.3) == 0.0, "空曲线返回 0")
check(abs(eval_curve([(0.3, 0.7)], 0.9) - 0.7) < 1e-6, "单点曲线为常数")

print()
print("3. XInput 后端自检")
backend = xinput_backend.get_backend()
print(f"  可用性      : {backend.available}")
print(f"  加载的 DLL  : {backend.dll_name or '(无)'}")
if not backend.available:
    print(f"  加载错误    : {backend.load_error}")
devices = backend.enumerate()
for info in devices:
    print(f"  {info.label}")
if len(devices) != 4:
    failures.append("设备枚举返回值数量不为 4")

print()
print("4. 震动引擎自检（无手柄时应安全降级）")
engine = RumbleEngine(tick_hz=125)
engine.start()
engine.update_params(master=0.8, waveform="storm")
engine.set_running(True)
time.sleep(1.0)
engine.set_running(False)
time.sleep(0.4)
engine.shutdown()

check(len(engine.history) > 0, f"引擎产生了历史样本 {len(engine.history)} 条")
check(engine.left_raw == 0 and engine.right_raw == 0, "停止后马达输出已归零")
check(engine.last_error == "" or not backend.available,
      f"引擎无异常（last_error={engine.last_error!r}）")
print(f"  连接状态    : {engine.connected}")
print(f"  实测频率    : {engine.measured_hz:.1f} Hz" if engine.measured_hz else "  实测频率    : (无手柄，未计时)")

if backend.available and engine.measured_hz:
    check(engine.measured_hz > 100, f"震动刷新率 {engine.measured_hz:.1f}Hz 应 > 100Hz")

print()
print("5. 分类清单")
for cat, items in waveforms_by_category():
    print(f"  {cat}: " + " / ".join(w.name for w in items))

print()
print("6. 虚拟波束自检")
from core.beam import BeamParams, BeamProcessor  # noqa: E402

bp = BeamProcessor()

gl, gr = bp.focus_gains(0.0, 0.45)
check(abs(gl - 1.0) < 1e-6 and abs(gr - 1.0) < 1e-6, "居中时左右增益均为 1.0（聚合）")

gl, gr = bp.focus_gains(-1.0, 1.0)
check(gl > 0.99 and gr < 0.01, f"最左时左满右空 (L={gl:.2f} R={gr:.2f})")

gl, gr = bp.focus_gains(1.0, 1.0)
check(gr > 0.99 and gl < 0.01, f"最右时右满左空 (L={gl:.2f} R={gr:.2f})")

# 聚焦度：波束越窄，偏离中心时衰减越快
_, narrow = bp.focus_gains(0.3, 0.05)
_, wide = bp.focus_gains(0.3, 1.0)
check(narrow <= wide, f"窄波束衰减更快 (窄={narrow:.2f} <= 宽={wide:.2f})")

env_off = bp.beat_envelope(0.0, 0.9, 0.0)
check(env_off == 1.0, "拍频关闭时包络恒为 1")
envs = [bp.beat_envelope(2.0, 0.9, i / 200.0) for i in range(200)]
check(min(envs) < 0.2 and max(envs) > 0.95,
      f"拍频包络起伏正常 ({min(envs):.2f} ~ {max(envs):.2f})")

p = BeamParams(enabled=True, position=0.0, width=0.5, beat_hz=0.0)
l, r, pos = bp.process(1.0, 1.0, p, 0.008, 0.0)
check(l > 0.99 and r > 0.99, f"波束居中且无拍频时两路满幅 ({l:.2f}, {r:.2f})")

p = BeamParams(enabled=True, position=-1.0, width=0.1)
l, r, pos = bp.process(1.0, 1.0, p, 0.008, 0.0)
check(l > 0.9 and r < 0.1, f"波束推到最左 ({l:.2f}, {r:.2f})")

check(BeamProcessor.polarity_phase_shift(BeamParams(polarity="out")) == 0.5,
      "反相极性产生半周期偏移")
check(BeamProcessor.polarity_phase_shift(BeamParams(polarity="in")) == 0.0,
      "同相极性无偏移")

print()
print("7. 随机搭配自检")
from core.waveforms import WAVEFORMS as _WF, random_preset  # noqa: E402

seen: set[str] = set()
for _ in range(300):
    rp = random_preset()
    if rp.waveform not in _WF:
        failures.append(f"随机搭配给出了不存在的波形 {rp.waveform}")
        break
    if rp.waveform_b and rp.waveform_b not in _WF:
        failures.append(f"随机搭配给出了不存在的混合波形 {rp.waveform_b}")
        break
    if not (0.0 <= rp.mix <= 1.0 and 0.0 <= rp.floor <= 1.0):
        failures.append(f"随机搭配参数越界 mix={rp.mix} floor={rp.floor}")
        break
    if not (-1.0 <= rp.beam_position <= 1.0):
        failures.append(f"随机搭配波束位置越界 {rp.beam_position}")
        break
    seen.add(rp.waveform)
check(len(seen) >= 12, f"300 次随机覆盖了 {len(seen)} 个不同波形（要求 >= 12）")

spicy = [random_preset(spicy=True).waveform for _ in range(150)]
hot = {w.key for w in _WF.values() if w.intensity in ("刺激", "极刺激")}
check(len(hot) >= 10, f"刺激档波形共 {len(hot)} 个")
check(all(k in hot for k in spicy),
      f"偏刺激模式下只挑刺激档波形（抽到 {len(set(spicy))} 个，全部命中）")

params = random_preset().to_params()
check(all(k in __import__("core.rumble_engine", fromlist=["EngineParams"]).EngineParams.__dataclass_fields__
          for k in params), "随机搭配的字段全部能被引擎接受")

print()
print("8. 界面音效自检")
from core import sfx  # noqa: E402

for name in sfx.RECIPES:
    data = sfx.render(name, 0.45)
    check(data[:4] == b"RIFF" and len(data) > 500,
          f"音效 {name:<11} 合成正常（{len(data)} bytes）")
check(len(sfx.render("click", 0.9)) == len(sfx.render("click", 0.9)),
      "音效合成结果可复现")
p = sfx.SfxPlayer(enabled=True)
p.preload()
check(p.available == (__import__("sys").platform == "win32"),
      f"winsound 可用性 = {p.available}")

print()
print("9. 音频后端自检")
try:
    from core.audio import AudioHub, LoopbackCapture, TIMBRES  # noqa: E402

    hub = AudioHub.instance()
    check(isinstance(hub.error, str), f"音频中心初始化（available={hub.available}）")
    if hub.available:
        devices = hub.list_loopback_devices()
        check(len(devices) > 0, f"找到 {len(devices)} 个 Loopback 设备")
        for d in devices[:4]:
            print(f"        - {d.label}")
        out = hub.default_output()
        check(out is not None, f"默认输出设备 = {out.name if out else None}")

        cap = LoopbackCapture()
        if cap.start():
            import time as _t
            _t.sleep(0.9)
            st = cap.state
            print(f"        采集 1 秒：低频={st.bass:.3f} 中高={st.mid:.3f} 高频={st.high:.3f}")
            check(st.capturing or not st.error, f"采集通道正常（err={st.error!r}）")
            cap.stop()
        else:
            print(f"        （采集未启动：{cap.state.error}）")
        check("rumble" in TIMBRES and "grain" in TIMBRES, "音色表齐全")
    else:
        print("        （音频不可用，跳过设备检测）")
except Exception as exc:
    import traceback
    print("        音频自检异常：")
    traceback.print_exc()
    failures.append(f"音频模块自检异常：{exc}")

print()
print("10. 体感增强自检（干跑模式，不需要手柄）")


def capture_env(waveform: str, seconds: float = 1.0, master: float = 1.0,
                warmup: float = 0.35, **params) -> list[tuple[float, float]]:
    """用干跑模式跑一段引擎，抓下运行期间的每帧输出包络。

    warmup 要留够：引擎启动后可能先在空闲态睡一轮，加上包络收敛需要时间。
    """
    eng = RumbleEngine(tick_hz=125)
    eng.dry_run = True
    frames: list[tuple[float, float]] = []
    eng.frame_sink = lambda a, b: frames.append((a, b))
    eng.start()
    eng.update_params(waveform=waveform, master=master, **params)
    eng.set_running(True)
    time.sleep(warmup)
    frames.clear()                 # 丢掉启动瞬态与包络爬升段
    time.sleep(seconds)
    eng.frame_sink = None          # 停止采集，免得把停止后的 0 也算进去
    eng.set_running(False)
    time.sleep(0.3)
    eng.shutdown()
    return frames


def env_stats(frames):
    left = [f[0] for f in frames]
    if not left:
        return 0.0, 0.0, 1.0
    mean = sum(left) / len(left)
    peak = max(left)
    zeros = sum(1 for v in left if v <= 0.001) / len(left)
    return peak, mean, zeros


# --- 基准：常震应该几乎不出现静默 ---
base_frames = capture_env("steady")
peak, mean, zeros = env_stats(base_frames)
check(len(base_frames) > 100, f"干跑模式抓到 {len(base_frames)} 帧输出")
check(peak > 0.95 and mean > 0.9, f"常震基准：峰值 {peak:.2f} 均值 {mean:.2f}")
check(zeros < 0.03, f"常震静默占比 {zeros:.0%}（应接近 0）")

# --- 占空比：对起伏波形压窄脉冲，静默占比应大幅上升 ---
# 注意 smoothing 会把门限填平，所以这里显式关掉平滑才看得到占空比的效果
sine_full = capture_env("sine", smoothing=0.0)
sine_duty = capture_env("sine", smoothing=0.0, duty=0.4)
_, _, z_full = env_stats(sine_full)
_, _, z_duty = env_stats(sine_duty)
check(z_duty > z_full + 0.25,
      f"占空比 40% 明显压窄脉冲（静默 {z_full:.0%} → {z_duty:.0%}）")

# --- 起停锐化：脉冲起始应有可见过冲 ---
soft = capture_env("tap", master=0.6, sharpen=0.0, smoothing=0.45)
sharp = capture_env("tap", master=0.6, sharpen=1.0, smoothing=0.45)
s_peak = max((f[0] for f in soft), default=0.0)
h_peak = max((f[0] for f in sharp), default=0.0)
check(h_peak > s_peak + 0.10,
      f"锐化产生起跳过冲（峰值 {s_peak:.3f} → {h_peak:.3f}）")

# --- 随机共振底噪：显著提高输出方差，但不抬高主峰值太多 ---
quiet = capture_env("steady", noise_floor=0.0, warmup=0.6)
noisy = capture_env("steady", noise_floor=1.0, warmup=0.6)


def variance(frames):
    vals = [f[0] for f in frames]
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / len(vals)


v_quiet = variance(quiet)
v_noisy = variance(noisy)
check(v_noisy > v_quiet * 5, f"底噪显著提高输出方差（{v_quiet:.2e} → {v_noisy:.2e}）")
q_peak = max((f[0] for f in quiet), default=0.0)
n_peak = max((f[0] for f in noisy), default=0.0)
check(n_peak - q_peak < 0.12, f"底噪幅度压在阈值内（峰值仅抬高 {n_peak - q_peak:.3f}）")

# --- 反适应漂移：长时间输出不应是完美常数，但也不能喧宾夺主 ---
drift = capture_env("steady", anti_adapt=1.0, seconds=3.0, warmup=0.8)
d_range = max(f[0] for f in drift) - min(f[0] for f in drift)
check(d_range > 0.01, f"反适应产生可见漂移（幅度 {d_range:.3f}）")
check(d_range < 0.16, f"漂移幅度压在 JND 之下（{d_range:.3f} < 0.16）")

print()
print("=" * 68)
if failures:
    print(f"自检未通过，共 {len(failures)} 项失败：")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("全部自检通过 ✔")

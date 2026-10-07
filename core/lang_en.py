"""English translations. Key = Chinese source string."""

TABLE = {
    # ---------------- 应用 ----------------
    "手柄震动 · 按摩控制器": "Gamepad Vibration Controller",
    "XInput 直驱　·　通用 Xbox 兼容手柄　·　125Hz 持续重发":
        "Direct XInput　·　Xbox-compatible gamepad　·　125 Hz continuous refresh",
    "目标设备": "Device",
    "重新扫描": "Rescan",
    "测试震动": "Test",
    "让手柄震 0.4 秒，用来确认链路通了": "Buzz for 0.4 s to verify the link",
    "未连接": "Not connected",
    "待机": "Idle",
    "未开启": "Off",
    "已连接 · 震动中": "Connected · Vibrating",
    "已连接 · 待机": "Connected · Idle",
    "正在检测…": "Detecting…",
    "缺少 XInput 运行库": "XInput runtime missing",
    "槽位 {i}　——　未连接": "Slot {i}　—　not connected",
    "槽位 {i}　Xbox 兼容手柄　[有线]": "Slot {i}　Xbox-compatible　[Wired]",
    "槽位 {i}　Xbox 兼容手柄　[无线]": "Slot {i}　Xbox-compatible　[Wireless]",
    "（无震动支持）": " (no rumble)",

    # ---------------- 左栏 ----------------
    "运行控制": "Run",
    "开 始 震 动": "S T A R T",
    "停 止 震 动": "S T O P",
    "强度调节": "Intensity",
    "总强度": "Master",
    "左马达": "Left motor",
    "右马达": "Right motor",
    "全局缩放系数，乘在左右马达之上": "Global scale applied on top of both motors",
    "左侧大马达：低频重震": "Left large motor: low-frequency, heavy",
    "右侧小马达：高频细震": "Right small motor: high-frequency, fine",
    "随机搭配": "Random mix",
    "随机一个": "Roll",
    "偏刺激": "Intense only",
    "偏刺激：开": "Intense: on",
    "偏刺激：关": "Intense: off",
    "自动轮换": "Auto rotate",
    "自动轮换：开": "Auto rotate: on",
    "自动轮换：关": "Auto rotate: off",
    "轮换间隔": "Interval",
    "每隔多久换一套随机搭配。切换会自动对齐到波形循环的接缝处":
        "How often to roll a new mix. Switching aligns to the waveform loop seam.",
    "保存配置": "Save",
    "载入配置": "Load",
    "恢复默认": "Reset",
    "导出预设…": "Export…",
    "导入预设…": "Import…",
    "音效：开": "Sound: on",
    "音效：关": "Sound: off",
    "帮助": "Help",
    "快捷键：空格 开始/停止　·　Esc 立即停止　·　R 随机搭配":
        "Keys: Space start/stop　·　Esc stop　·　R roll",
    "⚠ 未做功率限制。长时间全功率震动可能让马达过热、缩短寿命、掉电飞快，建议一轮 15~20 分钟。":
        "⚠ No power limit. Long full-power sessions can overheat the motors, shorten "
        "their life and drain the battery fast. 15–20 minutes per session is advised.",

    # ---------------- 标签页 ----------------
    "波形库": "Library",
    "波形参数": "Shape",
    "体感增强": "Enhance",
    "虚拟波束": "Beam",
    "自定义曲线": "Editor",
    "音频跟随": "Audio",

    # ---------------- 波形参数页 ----------------
    "这里调波形的形状、节奏与手感。所有改动即时生效。":
        "Shape, tempo and feel. Changes apply instantly.",
    "双波形混合": "Mix two waveforms",
    "混合波形": "Second",
    "混合比": "Blend",
    "（不混合）": "(none)",
    "0% = 只用主波形，100% = 只用混合波形。中间值会混出原库里没有的新节奏":
        "0% = first waveform only, 100% = second only. In between blends brand-new rhythms.",
    "节奏与手感": "Tempo & feel",
    "速度": "Speed",
    "波形循环快慢。1.00x 为原始节奏": "Loop rate. 1.00x is the original tempo.",
    "强度下限": "Floor",
    "常驻底噪：让马达一直在震，波形叠加在其之上":
        "Constant baseline so the motors never fully stop; the waveform rides on top.",
    "平滑": "Smoothing",
    "输出低通滤波，越大越绵软、启停越柔和": "Output low-pass. Higher = softer, gentler starts.",
    "相位差": "Phase",
    "右马达相对左马达的时间偏移，用于左右推移效果":
        "Time offset of the right motor relative to the left — creates left/right travel.",

    # ---------------- 体感增强页 ----------------
    "四个绕开马达物理短板的手段。默认值已经调好，可以逐项开关对比，详细说明见「帮助」。":
        "Four ways around the motor's physical limits. Defaults are already tuned — "
        "toggle each to compare. See Help for details.",
    "起停锐化": "Kick & Cut",
    "锐化强度": "Amount",
    "让短脉冲变脆。对敲击、拍打、连击、电脉冲最明显。":
        "Makes short pulses crisp. Most obvious on Tap, Spank, Drumroll and Electro.",
    "反适应漂移": "Anti-adaptation",
    "漂移量": "Amount",
    "防止长时间震动后「震麻了」。挂机时开着。":
        "Prevents the numb feeling during long sessions. Keep it on when idling.",
    "随机共振底噪": "Stochastic floor",
    "底噪强度": "Amount",
    "加一层听不见的微震，让上面的信号更清楚。开一点点就够。":
        "Adds an inaudible micro-vibration that sharpens the signal above it. A little is plenty.",
    "占空比": "Duty cycle",
    "压缩脉冲宽度。调小会把持续推压变成密集点刺。":
        "Narrows the pulses. Lower values turn a steady push into rapid pricks.",

    # ---------------- 虚拟波束页 ----------------
    "两个马达做不到在内部真正聚焦振动，这里做的是三件真实成立的事："
    "振幅声像（真实）、拍频干涉（真实物理）、同相聚合与反相分离（体感错觉）。"
    "详细说明见「帮助」。":
        "Two motors cannot truly focus vibration inside the shell. What is real here: "
        "amplitude panning (real), beat interference (real physics), and in-phase "
        "aggregation vs. anti-phase separation (a perceptual illusion). See Help.",
    "开关": "Switches",
    "波束": "Beam",
    "波束：开": "Beam: on",
    "波束：关": "Beam: off",
    "自动扫掠": "Auto sweep",
    "自动扫掠：开": "Auto sweep: on",
    "自动扫掠：关": "Auto sweep: off",
    "可以直接在顶部「聆听波束」面板的图上点击或拖动来设定位置。":
        "Click or drag on the Listen panel above to set the position.",
    "位置与聚焦": "Position & focus",
    "位置": "Position",
    "-100% 全在左握把，0 中央聚合，+100% 全在右握把":
        "-100% left grip, 0 centred, +100% right grip",
    "聚焦度": "Focus",
    "数值越大波束越窄、定位越锐利；越小越弥散":
        "Higher = tighter beam and sharper localisation; lower = broader.",
    "极性": "Polarity",
    "同相 · 中央聚合": "In phase · centred",
    "反相 · 两边轮流": "Anti-phase · alternating",
    "运动与干涉": "Motion & interference",
    "拍频": "Beat",
    "真实物理干涉：1~6Hz 体感最明显，会感受到一阵阵的涌动":
        "Real physical interference. 1–6 Hz is most noticeable — you feel surges.",
    "扫掠速度": "Sweep rate",
    "波束左右来回扫掠的速度": "How fast the beam sweeps left and right",
    "居中": "Centre",
    "偏左": "Left",
    "偏右": "Right",

    # ---------------- 音频跟随页 ----------------
    "抓系统全局回放，任何软件在放声音都能跟随。"
    "低频驱动左马达，中高频驱动右马达 —— 按两个马达的物理特性分配。":
        "Captures system playback, so anything making sound is followed. "
        "Bass drives the left motor, mids and highs the right — matching each motor's physics.",
    "采集": "Capture",
    "音频跟随": "Audio follow",
    "音频跟随：开": "Audio follow: on",
    "音频跟随：关": "Audio follow: off",
    "模式": "Mode",
    "只放波形": "Waveform only",
    "跟随音频": "Audio only",
    "波形 × 音频": "Waveform × audio",
    "采集源": "Source",
    "刷新": "Refresh",
    "重新枚举 WASAPI Loopback 设备": "Re-scan WASAPI loopback devices",
    "分频映射": "Band mapping",
    "低频→左": "Bass→L",
    "中高→右": "Mid→R",
    "20~120Hz 低频能量驱动左马达的增益": "Gain of 20–120 Hz energy driving the left motor",
    "120~4000Hz 中高频能量驱动右马达的增益": "Gain of 120–4000 Hz energy driving the right motor",
    "采集灵敏度": "Sensitivity",
    "对采集到的音频能量整体放大的倍数": "Overall gain applied to the captured audio energy",
    "触发阈值": "Threshold",
    "低于该能量的声音不驱动震动，用来滤掉底噪":
        "Sound below this level will not drive vibration — filters out the noise floor.",
    "采集未开启": "Capture off",
    "⚠ 聆听 + 音频跟随同时开启，已挖掉载波频段防回授":
        "⚠ Listening and audio-follow are both on — carrier bands notched out to stop feedback",
    "正在播放波束立体声": "Playing beam stereo",
    "手柄震动中（未聆听）": "Vibrating (not listening)",
    "（波形 × 音频模式下，波形会先被音频能量调制）":
        "(In Waveform × Audio mode the waveform is modulated by the audio energy.)",

    # ---------------- 自定义曲线页 ----------------
    "左键空白处加点并拖动　·　右键或双击删除控制点　·　滚轮在点上微调高度。"
    "曲线首尾自动闭合，无限循环。":
        "Left-click empty space to add a point and drag it　·　right-click or double-click "
        "to delete　·　scroll on a point to nudge its height. The curve wraps seamlessly.",
    "循环时长": "Loop length",
    "重置为直线": "Reset to flat",
    "清空": "Clear",
    "使用这条曲线": "Use this curve",
    "正在使用 ✓": "In use ✓",
    "点击空白处添加控制点": "Click empty space to add a point",
    "循环起点": "Loop start",
    "循环终点": "Loop end",

    # ---------------- 聆听波束面板 ----------------
    "聆听波束": "Listen to the beam",
    "双马达立体声　·　左马达→左声道　右马达→右声道　·　用耳朵直接听波束的位置与移动":
        "Dual-motor stereo　·　left motor → left channel, right motor → right channel　·　"
        "hear where the beam is and how it moves",
    "开 启 聆 听": "L I S T E N",
    "关 闭 聆 听": "S T O P",
    "音量": "Volume",
    "聆听波束的播放音量": "Playback volume of the beam audio",
    "音色": "Timbre",
    "马达嗡鸣　58Hz": "Motor hum　58 Hz",
    "超低潜行　36Hz": "Sub rumble　36 Hz",
    "蜂鸣　168Hz": "Buzz　168 Hz",
    "颗粒摩擦　噪声": "Grain　noise",
    "左": "L",
    "右": "R",
    "左握把": "Left grip",
    "中央聚合": "Centred",
    "右握把": "Right grip",
    "最近约 4.8 秒": "last ~4.8 s",
    "已停止  ·  点「开始震动」启动": "Stopped  ·  press START to begin",

    # ---------------- 波形分类 ----------------
    "基础": "Basic",
    "按摩手法": "Massage",
    "节奏冲击": "Rhythm",
    "波形起伏": "Waves",
    "刺激": "Intense",
    "玩具模式": "Toy",
    "节律引导": "Guided rhythm",
    "特殊": "Special",
    "彩蛋": "Easter egg",
    "自定义": "Custom",

    # ---------------- 强度档位 ----------------
    "柔和": "Gentle",
    "适中": "Medium",
    "刺激": "Strong",
    "极刺激": "Extreme",

    # ---------------- 波形名 ----------------
    "常震": "Steady", "呼吸": "Breath", "正弦波": "Sine", "锯齿": "Sawtooth",
    "深度按摩": "Deep", "揉捏": "Knead", "推拿": "Shiatsu", "敲击": "Tap",
    "捶打": "Hammer", "按压": "Press", "刮痧": "Scrape", "针灸": "Acupuncture",
    "脉冲": "Pulse", "快脉冲": "Fast pulse", "连击": "Drumroll", "三连击": "Triple hit",
    "狂奔": "Gallop", "渐强爆发": "Buildup", "暴风": "Storm", "波浪": "Wave",
    "潮汐": "Tide", "海浪": "Surf", "涟漪": "Ripple", "阶梯": "Step",
    "上升": "Ramp", "蝴蝶": "Butterfly", "颤动": "Vibrato", "心跳": "Heartbeat",
    "搏动": "Throb", "心动加速": "Cardio", "电脉冲": "Electro", "抽搐": "Twitch",
    "逗弄": "Tease", "巅峰爆发": "Climax", "烟花": "Fireworks", "地震": "Earthquake",
    "拍打": "Spank", "吸吮": "Suction", "抽送": "Thrust", "摇头": "Shake",
    "蠕动": "Creep", "抖动": "Rattle", "变频率": "DJ mode", "咕噜": "Purr",
    "镇静节律": "Calm", "提神节律": "Energize", "4-7-8 呼吸": "4-7-8 Breathing",
    "融化": "Melt", "失重": "Float", "随机": "Random", "混沌": "Chaos",
    "摩斯码": "Morse", "递进": "Ladder", "电火花": "Spark", "滴落": "Drip",
    "推力": "Push", "频段切换": "Dual band", "渐快": "Glide", "577": "577",
    "手绘曲线": "Hand-drawn",

    # ---------------- 波形说明 ----------------
    "恒定满幅，最基础的持续震动": "Constant full output — the simplest continuous buzz",
    "正弦渐强渐弱，最柔和，适合长时间挂机": "Sine swell; softest, good for long idle sessions",
    "标准正弦起伏": "Plain sine",
    "线性爬升后瞬间归零，有周期性拉扯感": "Linear climb, then snap to zero",
    "低频大幅揉压，带常驻底噪": "Slow deep kneading with a baseline",
    "左右交替挤压，模拟人手抓揉（约 25 次/分）": "Alternating squeeze, about 25 per minute",
    "双马达相位错开 120°，掌根推压感": "Motors 120° apart — palm-heel pressure",
    "短促脉冲 + 指数衰减，约 0.5s 一次": "Short pulse with decay, about 0.5 s apart",
    "更慢更重的冲击，力度峰值高": "Slower, heavier impacts",
    "缓慢加压 → 保持 → 释放": "Slow press, hold, release",
    "单向拖拽，右马达快速扫过": "One-way drag with a fast right-motor sweep",
    "规律三点短促针刺，点穴感": "Three regular needle pricks, like acupressure",
    "50% 占空比方波，干脆有力": "50% duty square wave — crisp and firm",
    "高频方波串，密集震颤": "Fast square-wave train",
    "由弱到强的 14 连高速冲击，打桩机感": "14 accelerating impacts, like a jackhammer",
    "左 · 右 · 双 三段重击后休息": "Left · right · both, then rest",
    "长-短-短骑乘节奏，像马蹄": "Long-short-short gallop",
    "脉冲越来越密越来越强，最后砸下去": "Pulses get denser and stronger, then slam down",
    "双马达异频高速抖动，压迫感极强": "Both motors at different rates — very intense",
    "左右 180° 反相，强度来回推移": "180° anti-phase left/right travel",
    "长周期不对称缓涨缓落": "Long asymmetric rise and fall",
    "快涨慢落，一次一次的推力": "Fast rise, slow fall — one push at a time",
    "一串由强到弱、越来越密的连续波": "A decaying, densifying train of waves",
    "一级级往上爬，然后突然落回": "Steps up, then drops back",
    "线性渐强到顶后瞬间归零": "Linear ramp to peak, then instant zero",
    "左右高速交替 + 强弱包络": "Fast left/right alternation with an envelope",
    "高频小幅调制叠加在持续输出上": "Fast shallow modulation on a steady output",
    "咚-咚—停顿，双脉冲心跳包络": "Lub-dub, then a pause",
    "比心跳更重更快的持续搏动": "Heavier and faster than Heartbeat",
    "一圈内节拍越来越快，然后重置": "Tempo accelerates within one loop, then resets",
    "极短高频爆点，针刺感最强": "Very short, sharp spikes — the prickliest",
    "不规则多段短促抽动": "Irregular short twitches",
    "缓慢逼到临界，突然全部收回": "Slowly builds to the edge, then cuts out",
    "长时间蓄力，末段全功率乱震": "Long charge-up, then full-power chaos",
    "一圈里随机炸开多次，疏密不一（Lovense fireworks 思路）":
        "Random bursts scattered across the loop",
    "不规则剧烈抖动，双马达各走各的随机序列（Lovense earthquake）":
        "Irregular violent shake, each motor on its own random sequence",
    "一记干脆的拍击 + 长静默，比敲击更重更疏":
        "One crisp smack, then a long pause — heavier and sparser than Tap",
    "缓慢拉起 → 急促释放，模拟负压节奏": "Slow pull, quick release — a suction rhythm",
    "推入快、退出慢的规律推拉": "Fast in, slow out",
    "左右快速摆动，像拨浪鼓": "Fast left/right wagging",
    "缓慢爬行的强度变化，几乎察觉不到切换点":
        "Slow creeping intensity with no perceptible seams",
    "高频小幅断续，像牙齿打颤": "Fast shallow chatter, like chattering teeth",
    "一圈内三段变速（慢→快→极快），像 DJ 搓碟":
        "Three tempo zones per loop: slow → fast → frantic",
    "猫呼噜式的低频颤动，持续带颗粒感": "Low-frequency purring with a grainy texture",
    "慢速心跳，默认约 55 BPM。用速度滑杆可调 30~110 BPM —— "
    "慢于自身静息心率的节律有助于降唤醒、缓解紧张（Doppel 研究）":
        "Slow heartbeat, about 55 BPM by default. Speed adjusts it from 30 to 110 BPM — "
        "a rate slower than your resting heart rate helps lower arousal (Doppel study)",
    "快速心跳，默认约 109 BPM。速度调到 1.4x 约 150 BPM，用于唤醒/提神":
        "Fast heartbeat, about 109 BPM by default. 1.4x is roughly 150 BPM — good for waking up",
    "呼吸引导：吸气 4s → 屏息 7s → 呼气 8s，一圈 19s。"
    "震起来吸气，最强时屏息，弱下去时呼气":
        "Breathing guide: inhale 4 s → hold 7 s → exhale 8 s, 19 s per loop. "
        "Breathe in as it rises, hold at the peak, out as it fades",
    "强度整体缓慢滑落再缓缓拉起，没有明显节拍":
        "Gradual overall fade and return, with no clear beat",
    "缓慢漂浮，几乎无节拍，适合长时间挂着": "Drifting, almost beatless — good for long idle sessions",
    "随机保持 + 平滑过渡，完全不可预测": "Random holds with smooth transitions, fully unpredictable",
    "多频叠加，不规律但连续": "Layered frequencies — irregular but continuous",
    "以摩斯电码节奏震动（默认 SOS）": "Vibrates in Morse code (SOS by default)",
    "台阶式加速，一级比一级快、比一级强": "Ladder of accelerating, strengthening steps",
    "极短随机爆点，比电脉冲更疏、更不可预测":
        "Very short random spikes — sparser than Electro",
    "一记清脆落点 + 长静默，然后一记轻的": "One crisp drop, a long pause, then a light one",
    "强度缓慢爬升到顶然后突然全部收回，像被一遍遍推着走。"
    "思路来自电刺激设备的脉宽调制（郊狼的「推力」波形）":
        "Climbs slowly to the top then cuts out completely, like being pushed again and again. "
        "Borrowed from e-stim pulse-width modulation",
    "在「慢而重」和「快而细」两个节奏之间硬切，靠节奏突变制造冲击":
        "Hard-cuts between slow-and-heavy and fast-and-fine",
    "一圈之内节奏从慢平滑加快到快，越往后越密":
        "The tempo accelerates smoothly within a single loop",
    "作者 577 的专属波形。一圈约 24 秒，走完六幕："
    "铺垫 → 挑逗 → 涌动 → 加速 → 边缘 → 收束。"
    "整库的手段串成一条线，建议强度留到 70% 以上再点。":
        "577's signature waveform. About 24 s per loop across six acts: "
        "build-up → tease → surge → accelerate → edge → resolve. "
        "Turn the intensity past 70% before you press it.",

    # ---------------- 通用 ----------------
    "循环 {p:g}s　·　强度 {i}": "loop {p:g}s　·　{i}",

    # ---------------- 运行期动态文案 ----------------
    "正在运行中，测试震动已跳过（先停止再测试）": "Running — test skipped (stop first)",
    "无法加载 XInput 运行库": "Cannot load the XInput runtime",
    "音频不可用": "Audio unavailable",
    "开启失败": "Failed to start",
    "配置已保存到 ": "Config saved to ",
    "配置保存失败": "Failed to save config",
    "已从配置载入": "Loaded config from",
    "已恢复默认参数": "Defaults restored",
    "已导出": "Exported",
    "已导入": "Imported",
    "导出失败": "Export failed",
    "导入失败": "Import failed",
    "预设文件格式不正确": "Invalid preset file",
    "采集异常": "Capture error",
    "等待手柄接入…": "Waiting for a gamepad…",
    "震动中": "Vibrating",
    "节拍": "Rate",
    "波形": "Wave",
    "作者": "Author",
    "使用手册": "User manual",
    "关闭": "Close",
}

"""应用内使用手册 —— 五种语言，跟随界面语言切换。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from core import i18n
from core.i18n import tr

AUTHOR = "577"
VERSION = "1.0"

_STYLE = """
<style>
  body { font-size: 13px; line-height: 1.75; color: #2F2A2C; }
  h2 { font-size: 15px; color: #E8446F; margin: 18px 0 6px 0; }
  h2:first-child { margin-top: 0; }
  p, li { margin: 4px 0; }
  ul { margin: 4px 0 4px 0; padding-left: 20px; }
  code { background: #FDF6F9; padding: 1px 5px; border-radius: 4px; }
  .hint { color: #9A8A91; font-size: 12px; }
  .warn { color: #B26A00; background: #FFF6E5; padding: 8px 10px;
          border: 1px solid #F7DFB4; border-radius: 8px; display: block; margin: 8px 0; }
  .egg { color: #A855F7; font-weight: bold; }
</style>
"""


def _zh() -> str:
    return f"""
<h2>连接手柄</h2>
<p>用 <b>2.4G 接收器</b>或 <b>USB 数据线</b>连接。蓝牙不可用 ——
蓝牙模式下 Windows 把手柄识别为 DInput 设备，XInput 枚举不到它。</p>
<p>顶部下拉框会列出四个槽位，插着手柄的那个会标出「有线」或「无线」。</p>

<h2>开始与停止</h2>
<p>点「<b>开始震动</b>」后手柄会一直震下去，不限时长。再点一次停止，或直接按 <code>Esc</code>。</p>
<p>关闭窗口时程序会强制把马达归零，不会卡住不停。</p>

<h2>强度</h2>
<ul>
<li><b>总强度</b> —— 整体缩放</li>
<li><b>左马达</b> —— 左边大马达，低频重震</li>
<li><b>右马达</b> —— 右边小马达，高频细震</li>
</ul>
<p class="hint">右栏曲线显示当前实际输出值（0~65535）。</p>

<h2>波形库</h2>
<p>共 55 个波形，分 9 类。想直接上强度按这个顺序试：
敲击 → 连击 → 暴风 → 电脉冲 → 巅峰爆发。</p>
<p class="hint">另有一个叫 <span class="egg">577</span> 的彩蛋波形，一圈 24 秒走完六幕。</p>

<h2>体感增强</h2>
<ul>
<li><b>起停锐化</b> —— 让短脉冲变脆。对敲击、拍打、连击最明显</li>
<li><b>反适应漂移</b> —— 防止长时间震动后「震麻了」，挂机时开着</li>
<li><b>随机共振底噪</b> —— 加一层听不见的微震，让上面的信号更清楚</li>
<li><b>占空比</b> —— 压缩脉冲宽度，把持续推压变成密集点刺</li>
</ul>

<h2>虚拟波束</h2>
<p>两个马达做不到在内部真正聚焦振动，这里实现的是三件真实成立的事：</p>
<ul>
<li><b>振幅声像</b> —— 体感重心在左右之间移动（真实）</li>
<li><b>拍频干涉</b> —— 两马达转速差产生的节拍起伏（真实物理）</li>
<li><b>同相聚合 / 反相分离</b> —— 同相感觉聚在中间，反相感觉两边轮流（体感错觉）</li>
</ul>
<p class="hint">可以直接在顶部波束图上点击或拖动来设定位置。</p>

<h2>聆听波束</h2>
<p>左马达包络送到左声道，右马达包络送到右声道。<b>戴上耳机就能听见波束扫到哪边</b>，
这是验证波束最直接的办法。</p>
<p class="warn">别和「音频跟随」同时开启：聆听放出的声音会被重新采集，形成回授啸叫。
程序会自动挖掉载波频段并给出提示，但仍建议错开使用。</p>

<h2>音频跟随</h2>
<p>抓系统全局回放，任何软件在放声音都能跟随。低频驱动左马达，中高频驱动右马达。</p>
<p>三种模式：<b>只放波形</b> / <b>跟随音频</b> / <b>波形 × 音频</b>（用音乐给按摩节奏打拍子）。</p>

<h2>随机搭配</h2>
<p>按 <code>R</code> 或点「随机一个」抽一整套参数。打开「自动轮换」会定时更换，
切换自动对齐到波形循环的接缝处，听不出断点。</p>

<h2>自定义曲线</h2>
<p>左键点空白处加点并拖动，右键或双击删除，滚轮在点上微调高度。曲线首尾自动闭合。</p>

<h2>配置文件</h2>
<p>参数存在程序同目录的 <code>presets.json</code>，退出时自动保存，下次打开自动恢复。</p>

<h2>快捷键</h2>
<p><code>空格</code> 开始/停止　·　<code>Esc</code> 立即停止　·
<code>R</code> 随机搭配　·　<code>F1</code> 帮助</p>

<h2>注意事项</h2>
<p class="warn"><b>没有做功率限制。</b>长时间全功率震动可能让马达过热、缩短寿命、掉电飞快，
建议一轮 15~20 分钟。</p>
<p class="warn"><b>不要和游戏同时用。</b>本程序每 8ms 覆盖一次震动状态，
开着它游戏里就没有震动了。玩游戏前先停掉。</p>

<h2>关于</h2>
<p>作者：<b>{AUTHOR}</b>　·　版本 {VERSION}</p>
"""


def _en() -> str:
    return f"""
<h2>Connecting</h2>
<p>Use the <b>2.4G receiver</b> or a <b>USB cable</b>. Bluetooth will not work —
Windows exposes the pad as a DirectInput device over Bluetooth, so XInput cannot see it.</p>
<p>The dropdown at the top lists four slots; the one with your pad shows "Wired" or "Wireless".</p>

<h2>Start and stop</h2>
<p>Press <b>Start</b> and the pad vibrates indefinitely. Press again to stop, or hit <code>Esc</code>.</p>
<p>Closing the window forces the motors to zero so they never get stuck on.</p>

<h2>Intensity</h2>
<ul>
<li><b>Master</b> — overall scale</li>
<li><b>Left motor</b> — large motor, low frequency and heavy</li>
<li><b>Right motor</b> — small motor, high frequency and fine</li>
</ul>
<p class="hint">The graph on the right shows the live output values (0–65535).</p>

<h2>Library</h2>
<p>55 waveforms in 9 categories. To go straight for intensity, try:
Tap → Drumroll → Storm → Electro → Climax.</p>
<p class="hint">There is also an easter egg called <span class="egg">577</span> —
one 24-second loop across six acts.</p>

<h2>Enhance</h2>
<ul>
<li><b>Kick &amp; Cut</b> — makes short pulses crisp. Most obvious on Tap, Spank, Drumroll</li>
<li><b>Anti-adaptation</b> — stops the numb feeling during long sessions</li>
<li><b>Stochastic floor</b> — an inaudible micro-vibration that sharpens the signal</li>
<li><b>Duty cycle</b> — narrows pulses, turning a steady push into rapid pricks</li>
</ul>

<h2>Beam</h2>
<p>Two motors cannot truly focus vibration inside the shell. Three things here are real:</p>
<ul>
<li><b>Amplitude panning</b> — the perceived centre moves left and right (real)</li>
<li><b>Beat interference</b> — surges from the speed difference between motors (real physics)</li>
<li><b>In-phase vs. anti-phase</b> — centred vs. alternating (a perceptual illusion)</li>
</ul>
<p class="hint">Click or drag on the beam graph at the top to set the position.</p>

<h2>Listen to the beam</h2>
<p>The left motor's envelope goes to the left channel and the right motor's to the right.
<b>Put on headphones and you hear where the beam is.</b> It is the most direct way to check it.</p>
<p class="warn">Do not enable this together with Audio follow: the played sound gets captured again
and howls. The app notches out the carrier band automatically, but staggering them is cleaner.</p>

<h2>Audio follow</h2>
<p>Captures system playback, so anything making sound is followed.
Bass drives the left motor, mids and highs the right.</p>
<p>Three modes: <b>Waveform only</b> / <b>Audio only</b> / <b>Waveform × audio</b>
(the music sets the beat for the waveform).</p>

<h2>Random mix</h2>
<p>Press <code>R</code> or click <b>Roll</b> for a full random set. Turn on <b>Auto rotate</b>
to change on a timer — switching aligns to the waveform loop seam, so you never hear a cut.</p>

<h2>Curve editor</h2>
<p>Left-click empty space to add a point and drag it, right-click or double-click to delete,
scroll on a point to nudge its height. The curve wraps seamlessly.</p>

<h2>Config file</h2>
<p>Settings live in <code>presets.json</code> next to the program, saved on exit and restored on launch.</p>

<h2>Shortcuts</h2>
<p><code>Space</code> start/stop　·　<code>Esc</code> stop　·
<code>R</code> random　·　<code>F1</code> help</p>

<h2>Notes</h2>
<p class="warn"><b>There is no power limit.</b> Long full-power sessions can overheat the motors,
shorten their life and drain the battery fast. 15–20 minutes per session is advised.</p>
<p class="warn"><b>Do not use it while gaming.</b> The app overwrites the rumble state every 8 ms,
so in-game rumble stops working. Turn it off before you play.</p>

<h2>About</h2>
<p>Author: <b>{AUTHOR}</b>　·　version {VERSION}</p>
"""


def _ja() -> str:
    return f"""
<h2>接続</h2>
<p><b>2.4G レシーバー</b>か <b>USB ケーブル</b>で接続します。Bluetooth は使えません ——
Bluetooth では Windows が DirectInput 機器として認識するため、XInput から見えません。</p>
<p>上部のドロップダウンに 4 つのスロットが並び、接続中のものに「有線」「無線」が表示されます。</p>

<h2>開始と停止</h2>
<p>「<b>開始</b>」を押すと時間制限なく振動し続けます。もう一度押すか <code>Esc</code> で停止。</p>
<p>ウィンドウを閉じるとモーターは強制的にゼロになります。</p>

<h2>強さ</h2>
<ul>
<li><b>全体</b> —— 全体の倍率</li>
<li><b>左モーター</b> —— 大型モーター、低周波で重い</li>
<li><b>右モーター</b> —— 小型モーター、高周波で細かい</li>
</ul>
<p class="hint">右側のグラフに現在の出力値（0〜65535）が出ます。</p>

<h2>ライブラリ</h2>
<p>9 分類 55 波形。強度重視ならこの順で：
タップ → ドラムロール → 嵐 → エレクトロ → クライマックス。</p>
<p class="hint">「<span class="egg">577</span>」という隠し波形もあります（1 ループ 24 秒・6 幕構成）。</p>

<h2>体感強化</h2>
<ul>
<li><b>立ち上がり強化</b> —— 短いパルスをくっきり。タップ・スパンク・ドラムロールで顕著</li>
<li><b>慣れ防止</b> —— 長時間で感覚が鈍るのを防ぎます</li>
<li><b>確率共鳴ノイズ</b> —— 感じ取れない微振動で信号をはっきりさせます</li>
<li><b>デューティ比</b> —— パルス幅を狭め、連続的な押しを細かい刺激に変えます</li>
</ul>

<h2>ビーム</h2>
<p>2 つのモーターは内部で振動を集束できません。ここで実現しているのは 3 つ：</p>
<ul>
<li><b>振幅パンニング</b> —— 体感の中心が左右に動く（実在）</li>
<li><b>うなり干渉</b> —— モーターの回転差による強弱のうねり（実在の物理）</li>
<li><b>同相 / 逆相</b> —— 中央集約と左右交互（体感の錯覚）</li>
</ul>
<p class="hint">上部のビーム図をクリック／ドラッグしても位置を設定できます。</p>

<h2>ビームを聴く</h2>
<p>左モーターの包絡を左チャンネル、右モーターを右チャンネルへ。
<b>ヘッドホンをつければビームがどちらに寄っているか聞こえます。</b>最も確実な確認方法です。</p>
<p class="warn">「音に追従」と同時に使わないでください。再生音が再取得されてハウリングします。
搬送波帯域は自動で除去しますが、交互に使うのが安全です。</p>

<h2>音に追従</h2>
<p>システムの再生音を取得するので、どのソフトの音でも反応します。
低音は左モーター、中高音は右モーターへ。</p>
<p>3 つのモード：<b>波形のみ</b> / <b>音のみ</b> / <b>波形 × 音</b>（音楽で波形に拍を与える）。</p>

<h2>ランダム</h2>
<p><code>R</code> か「ランダム」で一式を抽選。「自動切替」を入れると定期的に切り替わり、
波形ループの継ぎ目に合わせるので切れ目が分かりません。</p>

<h2>エディタ</h2>
<p>空白を左クリックで点を追加してドラッグ、右クリックかダブルクリックで削除、
点上でホイールすると高さを微調整。曲線は端が自動でつながります。</p>

<h2>設定ファイル</h2>
<p>設定はプログラムと同じフォルダの <code>presets.json</code> に保存され、終了時に自動保存されます。</p>

<h2>ショートカット</h2>
<p><code>Space</code> 開始/停止　·　<code>Esc</code> 停止　·
<code>R</code> ランダム　·　<code>F1</code> ヘルプ</p>

<h2>注意</h2>
<p class="warn"><b>出力制限はありません。</b>全出力で長時間動かすとモーターが過熱し、
寿命が縮み、電池の減りも速くなります。1 回 15〜20 分を目安に。</p>
<p class="warn"><b>ゲームと同時に使わないでください。</b>8ms ごとに振動状態を上書きするため、
ゲーム内の振動が効かなくなります。プレイ前に停止してください。</p>

<h2>このアプリについて</h2>
<p>作者：<b>{AUTHOR}</b>　·　バージョン {VERSION}</p>
"""


def _ko() -> str:
    return f"""
<h2>연결</h2>
<p><b>2.4G 수신기</b> 또는 <b>USB 케이블</b>로 연결하세요. 블루투스는 안 됩니다 ——
블루투스에서는 Windows가 DirectInput 장치로 인식해 XInput이 잡지 못합니다.</p>
<p>상단 드롭다운에 슬롯 4개가 표시되고, 연결된 슬롯에는 "유선" 또는 "무선"이 붙습니다.</p>

<h2>시작과 정지</h2>
<p><b>시작</b>을 누르면 시간 제한 없이 계속 진동합니다. 다시 누르거나 <code>Esc</code>로 정지합니다.</p>
<p>창을 닫으면 모터가 강제로 0이 되어 멈추지 않는 일이 없습니다.</p>

<h2>강도</h2>
<ul>
<li><b>전체</b> — 전체 배율</li>
<li><b>왼쪽 모터</b> — 대형 모터, 저주파 강진동</li>
<li><b>오른쪽 모터</b> — 소형 모터, 고주파 미세진동</li>
</ul>
<p class="hint">오른쪽 그래프에 현재 출력값(0~65535)이 표시됩니다.</p>

<h2>라이브러리</h2>
<p>9개 분류, 55개 파형. 강도를 원하면 이 순서로:
타격 → 드럼롤 → 폭풍 → 일렉트로 → 클라이맥스.</p>
<p class="hint"><span class="egg">577</span>이라는 이스터에그 파형도 있습니다 (한 루프 24초, 6막).</p>

<h2>체감 강화</h2>
<ul>
<li><b>기동 샤프닝</b> — 짧은 펄스를 또렷하게. 타격·스팽크·드럼롤에서 두드러짐</li>
<li><b>적응 방지</b> — 오래 진동할 때 감각이 무뎌지는 것을 막습니다</li>
<li><b>확률 공명 노이즈</b> — 느껴지지 않는 미세 진동으로 신호를 또렷하게</li>
<li><b>듀티비</b> — 펄스 폭을 좁혀 지속 압박을 촘촘한 자극으로 바꿉니다</li>
</ul>

<h2>빔</h2>
<p>모터 두 개는 내부에서 진동을 실제로 집속할 수 없습니다. 여기서 실제인 것은 세 가지:</p>
<ul>
<li><b>진폭 패닝</b> — 체감 중심이 좌우로 이동 (실제)</li>
<li><b>맥놀이 간섭</b> — 모터 속도차로 생기는 강약의 물결 (실제 물리)</li>
<li><b>동상 / 역상</b> — 중앙 집중과 좌우 교대 (체감 착각)</li>
</ul>
<p class="hint">위쪽 빔 그림을 클릭하거나 드래그해 위치를 정할 수 있습니다.</p>

<h2>빔 듣기</h2>
<p>왼쪽 모터의 포락선은 왼쪽 채널, 오른쪽 모터는 오른쪽 채널로.
<b>헤드폰을 쓰면 빔이 어느 쪽으로 가는지 들립니다.</b> 가장 확실한 확인 방법입니다.</p>
<p class="warn">'오디오 추종'과 함께 켜지 마세요. 재생음이 다시 수집되어 하울링합니다.
반송파 대역은 자동으로 제거하지만 번갈아 쓰는 편이 안전합니다.</p>

<h2>오디오 추종</h2>
<p>시스템 재생음을 가져오므로 어떤 프로그램의 소리든 따라갑니다.
저음은 왼쪽 모터, 중고음은 오른쪽 모터로.</p>
<p>세 가지 모드: <b>파형만</b> / <b>오디오만</b> / <b>파형 × 오디오</b> (음악이 파형의 박자를 정합니다).</p>

<h2>랜덤 조합</h2>
<p><code>R</code> 또는 '랜덤'을 누르면 전체 설정을 뽑습니다. '자동 전환'을 켜면 주기적으로 바뀌고,
파형 루프 이음새에 맞춰 전환되어 끊김이 들리지 않습니다.</p>

<h2>편집기</h2>
<p>빈 곳을 왼쪽 클릭해 점을 추가하고 드래그, 오른쪽 클릭이나 더블 클릭으로 삭제,
점 위에서 휠로 높이를 미세 조정합니다. 곡선은 양 끝이 자동으로 이어집니다.</p>

<h2>설정 파일</h2>
<p>설정은 프로그램과 같은 폴더의 <code>presets.json</code>에 저장되고 종료 시 자동 저장됩니다.</p>

<h2>단축키</h2>
<p><code>Space</code> 시작/정지　·　<code>Esc</code> 정지　·
<code>R</code> 랜덤　·　<code>F1</code> 도움말</p>

<h2>주의</h2>
<p class="warn"><b>출력 제한이 없습니다.</b> 최대 출력으로 오래 진동하면 모터가 과열되고
수명이 줄며 배터리가 빨리 소모됩니다. 한 번에 15~20분을 권장합니다.</p>
<p class="warn"><b>게임과 동시에 쓰지 마세요.</b> 8ms마다 진동 상태를 덮어쓰기 때문에
게임 내 진동이 작동하지 않습니다. 플레이 전에 정지하세요.</p>

<h2>정보</h2>
<p>제작: <b>{AUTHOR}</b>　·　버전 {VERSION}</p>
"""


def _ru() -> str:
    return f"""
<h2>Подключение</h2>
<p>Используйте <b>ресивер 2.4G</b> или <b>кабель USB</b>. Bluetooth не подойдёт —
в этом режиме Windows видит геймпад как DirectInput, и XInput его не находит.</p>
<p>В списке сверху четыре слота; у подключённого будет пометка «кабель» или «радио».</p>

<h2>Пуск и остановка</h2>
<p>Нажмите <b>СТАРТ</b> — вибрация продолжится без ограничения по времени. Ещё раз или
<code>Esc</code> — стоп.</p>
<p>При закрытии окна моторы принудительно обнуляются и не застревают.</p>

<h2>Интенсивность</h2>
<ul>
<li><b>Общая</b> — общий множитель</li>
<li><b>Левый мотор</b> — крупный мотор, низкие частоты, тяжело</li>
<li><b>Правый мотор</b> — малый мотор, высокие частоты, тонко</li>
</ul>
<p class="hint">График справа показывает текущие значения выхода (0–65535).</p>

<h2>Библиотека</h2>
<p>55 волн в 9 категориях. Для максимальной интенсивности попробуйте по порядку:
Стук → Дробь → Шторм → Электро → Кульминация.</p>
<p class="hint">Есть и пасхалка <span class="egg">577</span> — 24 секунды на цикл, шесть актов.</p>

<h2>Усиление</h2>
<ul>
<li><b>Резкость старта</b> — делает короткие импульсы чёткими. Заметно на «Стук», «Шлепок», «Дробь»</li>
<li><b>Защита от привыкания</b> — не даёт ощущению притупиться при долгой работе</li>
<li><b>Стохастический фон</b> — неслышимая микровибрация, делающая сигнал чётче</li>
<li><b>Скважность</b> — сужает импульсы: ровный нажим превращается в частые уколы</li>
</ul>

<h2>Луч</h2>
<p>Два мотора не могут по-настоящему фокусировать вибрацию внутри корпуса. Реальны здесь три вещи:</p>
<ul>
<li><b>Панорама амплитуды</b> — ощущаемый центр смещается влево-вправо (реально)</li>
<li><b>Интерференция биений</b> — волны от разницы скоростей моторов (реальная физика)</li>
<li><b>Синфазно / противофазно</b> — центр против чередования (ощущенческая иллюзия)</li>
</ul>
<p class="hint">Позицию можно задать прямо на схеме луча сверху — кликом или перетаскиванием.</p>

<h2>Слушать луч</h2>
<p>Огибающая левого мотора идёт в левый канал, правого — в правый.
<b>Наденьте наушники, и вы услышите, куда смещён луч.</b> Это самый надёжный способ проверки.</p>
<p class="warn">Не включайте вместе со следованием за звуком: воспроизведение снова попадёт
в захват и возникнет завязка. Полосы несущей вырезаются автоматически, но лучше чередовать.</p>

<h2>Следование за звуком</h2>
<p>Захватывает системное воспроизведение, поэтому реагирует на любую программу.
Бас идёт в левый мотор, середины и высокие — в правый.</p>
<p>Три режима: <b>только волна</b> / <b>только звук</b> / <b>волна × звук</b>
(музыка задаёт ритм волне).</p>

<h2>Случайный набор</h2>
<p><code>R</code> или кнопка «Случайно» выдаёт полный набор параметров. Включите «Автосмену» —
смена привязана к стыку цикла волны, поэтому разрыва не слышно.</p>

<h2>Редактор</h2>
<p>ЛКМ по пустому месту добавляет точку, тянется мышью; ПКМ или двойной клик удаляет;
колесо на точке меняет высоту. Кривая замыкается автоматически.</p>

<h2>Файл настроек</h2>
<p>Параметры хранятся в <code>presets.json</code> рядом с программой и сохраняются при выходе.</p>

<h2>Горячие клавиши</h2>
<p><code>Space</code> пуск/стоп　·　<code>Esc</code> стоп　·
<code>R</code> случайно　·　<code>F1</code> справка</p>

<h2>Внимание</h2>
<p class="warn"><b>Ограничения мощности нет.</b> Долгая работа на полной мощности перегревает
моторы, сокращает срок службы и быстро сажает батарею. Ориентир — 15–20 минут за сеанс.</p>
<p class="warn"><b>Не используйте одновременно с играми.</b> Программа перезаписывает состояние
вибрации каждые 8 мс, поэтому в игре вибрация пропадёт. Остановите её перед игрой.</p>

<h2>О программе</h2>
<p>Автор: <b>{AUTHOR}</b>　·　версия {VERSION}</p>
"""


_BUILDERS = {"zh": _zh, "en": _en, "ja": _ja, "ko": _ko, "ru": _ru}


def manual_html(code: str | None = None) -> str:
    code = code or i18n.current()
    builder = _BUILDERS.get(code, _zh)
    return _STYLE + builder()


class ManualDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("使用手册"))
        self.setMinimumSize(760, 700)
        self.resize(820, 780)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addStretch(1)
        self.lang_combo = QComboBox()
        for code, name in i18n.available():
            self.lang_combo.addItem(name, code)
        idx = self.lang_combo.findData(i18n.current())
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language)
        top.addWidget(self.lang_combo)

        self.close_btn = QPushButton(tr("关闭"))
        self.close_btn.clicked.connect(self.accept)
        top.addWidget(self.close_btn)
        root.addLayout(top)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.browser.setHtml(manual_html())
        root.addWidget(self.browser, 1)

    def _on_language(self, _index: int) -> None:
        code = self.lang_combo.currentData()
        if code:
            self.browser.setHtml(manual_html(code))

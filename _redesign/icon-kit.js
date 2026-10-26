/* ============================================================================
   图标库 icon-kit —— 24×24 网格 / 1.8 描边 / currentColor
   ----------------------------------------------------------------------------
   为什么是"内部路径字符串"而不是一整个 <svg>：
   外壳（viewBox、描边、宽高、aria）每处都一样，只有里面的 d 不同。外壳只写一份，
   调用方永远只关心"哪个图标 + 多大/什么颜色"，尺寸交给 CSS 的 .ico 系列，颜色交给
   currentColor —— 这样深色模式、强调色、禁用态全都不用改图标代码。

   光学约定（改图标时请守住）：
   1. 所有图标的主体落在 3～21 之间（个别的圆/方到 3.4～20.6），视觉重量才一致；
      不要出现"某个图标看着比旁边小一圈"。
   2. 描边统一 1.8，端点圆角（由外壳的 stroke-linecap/linejoin 给）。
   3. 实心元素（播放三角、圆点、停止方块、四角星）要显式 fill="currentColor" stroke="none"，
      否则会继承 fill:none 变成"只有一个洞"。
   4. 细节直径 <2px 在 16px 渲染下必定糊掉 —— 宁可少画一根线。这条是硬约束：
      图标要在 16px 中文界面里认得出来。
   5. 名字用语义（play，不是 triangle），全小写 kebab-case。

   用法：
     el.innerHTML = icon('search');                  // 1em 大小，跟字号走
     '<button>' + icon('play','ico-16') + ' 可视化</button>'
     '<span class="chip">' + icon('book') + ' 讲义</span>'
   未知名字返回 ''（不抛错）：界面重试/占位时宁可少一个图标，也不能整段脚本炸掉。
   ============================================================================ */
var ICONS = {

  /* ---------------------------------------------------------------- 导航栏
     左侧 60px 深色脊上那 6 个 + 通用导航动作。 */

  // 目录：四级缩进的行，比纯列表更能表达"章 › 节 › 知识点"的层级
  'toc': '<path d="M4 5.6h16M7.4 10.2h12.6M7.4 14.8h12.6M10.8 19.4h9.2"/>',

  // 试一试（REPL）：终端窗 + 提示符 + 光标
  'terminal': '<rect x="3" y="4.6" width="18" height="14.8" rx="2.6"/><path d="M7.2 10.2l2.3 2-2.3 2"/><path d="M12.4 14.2h4.4"/>',

  // 可视化（单步执行 ▶|）：实心三角 + 竖杠。原来画的是"代码行+变量行+结点"，
  // 48px 下像 settings，16px 下完全分不清 —— 视觉可辨识度优先于语义的"具象化"。
  'visualize': '<path d="M7.4 5.4l9.4 6.6-9.4 6.6z" fill="currentColor" stroke="none"/><path d="M18.4 5.8v12.4"/>',

  // 视频：屏幕 + 播放三角（实心）
  'videos': '<rect x="3" y="5.4" width="18" height="13.2" rx="2.6"/><path d="M10 9.4v5.2l4.8-2.6z" fill="currentColor" stroke="none"/>',

  // 日历（100 Days / 截止日）：窗 + 顶部横线 + 两个装订脚 + 一个实心日点
  'calendar': '<rect x="3.4" y="5.2" width="17.2" height="15" rx="2.6"/><path d="M3.4 9.8h17.2M8.2 3.2v3.6M15.8 3.2v3.6"/><circle cx="12" cy="15" r="1.8" fill="currentColor" stroke="none"/>',

  // 作业：练习本（左侧装订线 + 右侧行）
  'homework': '<rect x="4.6" y="3.8" width="14.8" height="16.4" rx="2.6"/><path d="M8.2 3.8v16.4"/><path d="M11.4 9.2h4.6M11.4 12.8h4.6M11.4 16.4h2.8"/>',

  // 搜索：放大镜
  'search': '<circle cx="10.6" cy="10.6" r="5.9"/><path d="M14.9 14.9l4.6 4.6"/>',

  // 刷新（检查更新 / 重新生成 / 检查新作业）：开口圆环 + 箭头
  'refresh': '<path d="M19.6 12a7.6 7.6 0 1 1-2.2-5.4"/><path d="M19.7 4.7v3.7h-3.7"/>',

  // 设置：三横 + 三个实心钮。故意不用齿轮 —— 20 齿齿轮在 16px 下一定糊成一团，
  // 而"AI 设置"这个面板本来就是一排开关/输入框，滑杆更贴切。
  'settings': '<path d="M4 7h16M4 12h16M4 17h16"/><circle cx="9" cy="7" r="2.2" fill="currentColor" stroke="none"/><circle cx="15.4" cy="12" r="2.2" fill="currentColor" stroke="none"/><circle cx="7.6" cy="17" r="2.2" fill="currentColor" stroke="none"/>',
  'sliders': '<path d="M4 7h16M4 12h16M4 17h16"/><circle cx="9" cy="7" r="2.2" fill="currentColor" stroke="none"/><circle cx="15.4" cy="12" r="2.2" fill="currentColor" stroke="none"/><circle cx="7.6" cy="17" r="2.2" fill="currentColor" stroke="none"/>',

  // 关闭
  'close': '<path d="M5.6 5.6l12.8 12.8M18.4 5.6L5.6 18.4"/>',

  'chevron-left': '<path d="M14.8 6.2L9.2 12l5.6 5.8"/>',
  'chevron-right': '<path d="M9.2 6.2L14.8 12l-5.6 5.8"/>',
  'chevron-down': '<path d="M6.2 9.2L12 14.8l5.8-5.6"/>',
  'chevron-up': '<path d="M6.2 14.8L12 9.2l5.8 5.6"/>',

  // 外链（B站 ↗ / 去 OJ）
  'external-link': '<path d="M13.6 3.6h6.8v6.8"/><path d="M20.4 3.6l-9 9"/><path d="M17.6 14v4.4a2.4 2.4 0 0 1-2.4 2.4H5.6a2.4 2.4 0 0 1-2.4-2.4V8.4a2.4 2.4 0 0 1 2.4-2.4H10"/>',

  // 展开 / 收起：四角括号（⤢ 那个位置）
  'expand': '<path d="M9.4 3.6H3.6v5.8"/><path d="M14.6 3.6h5.8v5.8"/><path d="M20.4 14.6v5.8h-5.8"/><path d="M3.6 14.6v5.8h5.8"/>',
  'collapse': '<path d="M3.6 9.4h5.8V3.6"/><path d="M20.4 9.4h-5.8V3.6"/><path d="M14.6 20.4v-5.8h5.8"/><path d="M9.4 20.4v-5.8H3.6"/>',

  // 菜单（☰）
  'menu': '<path d="M4 7.2h16M4 12h16M4 16.8h16"/>',

  /* ------------------------------------------------------------ 内容与状态
     卡片流、代码块工具条、作业面板、设置页里真正用得上的那些。 */

  // 文档（讲义 notes.md / 任意 .md）：折角文件
  'document': '<path d="M13 3.6H7.2A2.4 2.4 0 0 0 4.8 6v12a2.4 2.4 0 0 0 2.4 2.4h9.6a2.4 2.4 0 0 0 2.4-2.4V9.8z"/><path d="M13.2 3.7V9.8h5.9"/>',

  // 书 / 教材（📖 100Days、参考代码）：画"摊开的书"而不是"带书签的合上的书" ——
  // 16px 下书签缩小成一个点点，反而让整个图标读成"折角文件"（和 document 撞车）。
  'book': '<path d="M3.6 4.2h4.2a4 4 0 0 1 4 4v12.2a3.2 3.2 0 0 0-3.2-3.2H3.6z"/><path d="M20.4 4.2h-4.2a4 4 0 0 0-4 4v12.2a3.2 3.2 0 0 1 3.2-3.2h5z"/>',

  // 图片 / 课件截图
  'image': '<rect x="3.4" y="4.6" width="17.2" height="14.8" rx="2.6"/><circle cx="8.4" cy="9.6" r="1.8" fill="currentColor" stroke="none"/><path d="M4.4 17.6l4.8-4.6 3.4 3.2 2.6-2.4 4.4 4.2"/>',

  // 链接（🔗 外部参考）
  'link': '<path d="M10.4 13.6a3.8 3.8 0 0 0 5.4 0l3-3a3.8 3.8 0 0 0-5.4-5.4l-1.1 1.1"/><path d="M13.6 10.4a3.8 3.8 0 0 0-5.4 0l-3 3a3.8 3.8 0 0 0 5.4 5.4l1.1-1.1"/>',

  // 图钉（📌 本章总结 / 固定引用）：用"定位针"（水滴 + 孔）而不是侧视的图钉 ——
  // 侧视图钉在 16px 下只剩一根针，认不出；水滴形在小尺寸下最稳。
  'pin': '<path d="M12 20.6c3.7-4.5 5.9-7.5 5.9-10.4a5.9 5.9 0 0 0-11.8 0c0 2.9 2.2 5.9 5.9 10.4z"/><circle cx="12" cy="9.9" r="2.3"/>',

  // 播放（▶ 可视化 / 运行）—— 实心三角，右侧留 1.5 让它光学居中
  'play': '<path d="M8.2 4.8L18.4 12L8.2 19.2z" fill="currentColor" stroke="none"/>',

  // 复制（📋）：两张纸
  'copy': '<rect x="8.4" y="8.4" width="11.8" height="11.8" rx="2.6"/><path d="M15.6 5.6H6.4A2.4 2.4 0 0 0 4 8v9.2"/>',

  // 通过（✅）
  'check': '<path d="M4.8 12.6l4.7 4.7L19.2 7.2"/>',
  // 失败（❌）
  'cross': '<path d="M5.8 5.8l12.4 12.4M18.2 5.8L5.8 18.2"/>',
  'check-circle': '<circle cx="12" cy="12" r="8.4"/><path d="M7.9 12.1l2.9 2.9 5.3-5.9"/>',
  'x-circle': '<circle cx="12" cy="12" r="8.4"/><path d="M9.2 9.2l5.6 5.6M14.8 9.2l-5.6 5.6"/>',

  // 警告（⚠️ 待确认 / 点坑 / 无法验证）
  'warning': '<path d="M12 4.1L20.5 19.2H3.5z"/><path d="M12 9.8v3.7"/><circle cx="12" cy="16.5" r="1.05" fill="currentColor" stroke="none"/>',

  // 信息（提示条）
  'info': '<circle cx="12" cy="12" r="8.4"/><path d="M12 11.2v5"/><circle cx="12" cy="7.9" r="1.05" fill="currentColor" stroke="none"/>',

  // 灯泡（💡 提示）：穹顶 + 灯颈 + 灯头
  'lightbulb': '<path d="M8.4 13.9a5.6 5.6 0 1 1 7.2 0v2.3H8.4z"/><path d="M10.4 18.7h3.2"/>',

  // 停止（⏹ 停止生成 / 全跑一遍的中断）—— 实心方块
  'stop': '<rect x="5.8" y="5.8" width="12.4" height="12.4" rx="2.4" fill="currentColor" stroke="none"/>',

  // 火箭（🚀 自动提交）：弹体 + 两片尾翼
  'rocket': '<path d="M12 3.4c2.6 2.2 4 5.2 4 8.6v5.2H8V12c0-3.4 1.4-6.4 4-8.6z"/><path d="M8 13.4l-2.8 3.2v2.8l2.8-1.8"/><path d="M16 13.4l2.8 3.2v2.8l-2.8-1.8"/><path d="M10.4 17.6l1.6 2.8 1.6-2.8"/>',

  // 助教（🤖）：头 + 天线 + 两眼 + 嘴
  'robot': '<rect x="4.2" y="7.8" width="15.6" height="11.6" rx="3.2"/><path d="M12 4.4v3.4"/><circle cx="12" cy="3.7" r="1.2" fill="currentColor" stroke="none"/><circle cx="9.4" cy="12.6" r="1.35" fill="currentColor" stroke="none"/><circle cx="14.6" cy="12.6" r="1.35" fill="currentColor" stroke="none"/><path d="M9.8 16.2h4.4"/>',

  // 清空（🧹）：斜柄 + 斜的刷头 + 一根刷毛
  'broom': '<path d="M19.4 4.6L12.7 11.3"/><path d="M14.4 9.6L11 13L5.7 15.5L8.5 18.3Z"/><path d="M12.7 11.3L7.1 16.9"/>',

  // AI 生成（✨ / 让 AI 看看）：两颗实心四角星
  'sparkle': '<path d="M10.4 3.6L12.1 8.1L16.6 9.8L12.1 11.5L10.4 16L8.7 11.5L4.2 9.8L8.7 8.1Z" fill="currentColor" stroke="none"/><path d="M17.4 14.6L18.2 16.7L20.3 17.5L18.2 18.3L17.4 20.4L16.6 18.3L14.5 17.5L16.6 16.7Z" fill="currentColor" stroke="none"/>',

  // 终点旗（🏁 全跑一遍 / 走完了）
  'flag': '<path d="M6.2 3.8v16.4"/><path d="M6.2 4.8h11.4l-2.4 4 2.4 4H6.2"/>',

  // 空（📭 没有视频 / 没有作业）
  'inbox': '<path d="M3.4 12.4h4.5l1.7 2.8h4.8l1.7-2.8h4.5"/><path d="M6.6 4.6h10.8l3.2 7.8v5a2.4 2.4 0 0 1-2.4 2.4H5.8a2.4 2.4 0 0 1-2.4-2.4v-5z"/>',

  // 视频目录 / UP 主（📺 🎬）：胶片格
  'film': '<rect x="3.4" y="4.8" width="17.2" height="14.4" rx="2.6"/><path d="M8.2 4.8v14.4M15.8 4.8v14.4"/><path d="M3.4 9.4h4.8M3.4 14.6h4.8M15.8 9.4h4.8M15.8 14.6h4.8"/>',

  // 列表（作业列表 / 用例列表）
  'list': '<path d="M8.8 6.2h11M8.8 12h11M8.8 17.8h11"/><circle cx="4.9" cy="6.2" r="1.3" fill="currentColor" stroke="none"/><circle cx="4.9" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="4.9" cy="17.8" r="1.3" fill="currentColor" stroke="none"/>',

  // 时间（截止 ⏰ / 耗时）
  'clock': '<circle cx="12" cy="12" r="8.4"/><path d="M12 6.8v5.4l3.6 2.2"/>',

  // 目标（🎯 本章要学什么）
  'target': '<circle cx="12" cy="12" r="8.4"/><circle cx="12" cy="12" r="2.9" fill="currentColor" stroke="none"/>',

  // 奖章（完结 / 成就）
  'award': '<circle cx="12" cy="9.6" r="5.6"/><path d="M8.5 14.4L6.8 20.4l5.2-2.9 5.2 2.9-1.7-6"/>',

  // 调试 / 错误排查
  'bug': '<rect x="8.2" y="7.4" width="7.6" height="10.8" rx="3.8"/><path d="M8.2 11.2H5M8.2 15.4l-2.6 2M15.8 11.2H19M15.8 15.4l2.6 2M9.8 7.4L8.4 5.2M14.2 7.4l1.4-2.2"/>',

  // 代码（</>）
  'code': '<path d="M8.6 7.8L4 12l4.6 4.2"/><path d="M15.4 7.8L20 12l-4.6 4.2"/><path d="M13.6 4.8l-3.2 14.4"/>',

  // Python（🐍）：两条盘绕的蛇身（Python 官方标志的两个"钩"的极简化）
  'python': '<path d="M11.8 3.8H9.4a3.6 3.6 0 0 0-3.6 3.6v2.4c0 1.5 1.2 2.7 2.7 2.7h7"/><path d="M12.2 20.2h2.4a3.6 3.6 0 0 0 3.6-3.6v-2.4c0-1.5-1.2-2.7-2.7-2.7H8.6"/>',

  // 试管（🧪 跑一下 / 用样例测 / 小测）：管身 + 液面线
  'test-tube': '<path d="M9.4 3.6h5.2"/><path d="M10.6 3.6v12.6a2.4 2.4 0 0 0 4.8 0V3.6"/><path d="M10.6 12.6h4.8"/>',

  // 目录 / 文件夹（课件原图）
  'folder': '<path d="M3.6 7.6a2.6 2.6 0 0 1 2.6-2.6h3.2l2.2 2.8H18a2.6 2.6 0 0 1 2.6 2.6v6.8a2.6 2.6 0 0 1-2.6 2.6H6.2a2.6 2.6 0 0 1-2.6-2.6z"/>',

  // 上传（📤 复制并去提交）
  'upload': '<path d="M12 16.2V4.2"/><path d="M7.6 8.6L12 4.2l4.4 4.4"/><path d="M4.6 15.4v2.8a2.2 2.2 0 0 0 2.2 2.2h10.4a2.2 2.2 0 0 0 2.2-2.2v-2.8"/>',
  // 下载（⬇ 安装这一章）
  'download': '<path d="M12 4.2v12"/><path d="M7.6 11.8L12 16.2l4.4-4.4"/><path d="M4.6 15.4v2.8a2.2 2.2 0 0 0 2.2 2.2h10.4a2.2 2.2 0 0 0 2.2-2.2v-2.8"/>',

  // Key（🔑 登录 / AI Key）
  'key': '<circle cx="8.2" cy="15.8" r="3.6"/><path d="M10.8 13.2L19.4 4.6"/><path d="M16.4 7.6l2.2 2.2M13.8 10.2l2.2 2.2"/>',

  // 余额（💰）：钱包 + 扣子
  'wallet': '<path d="M3.8 8.2a2.4 2.4 0 0 1 2.4-2.4h10.4"/><rect x="3.8" y="5.8" width="16.4" height="12.8" rx="2.6"/><circle cx="16.8" cy="12.2" r="1.3" fill="currentColor" stroke="none"/>',

  // 站点 / 环境（外部链接的地球）
  'globe': '<circle cx="12" cy="12" r="8.4"/><path d="M3.6 12h16.8"/><path d="M12 3.6c2.3 2.4 3.5 5.3 3.5 8.4s-1.2 6-3.5 8.4c-2.3-2.4-3.5-5.3-3.5-8.4s1.2-6 3.5-8.4z"/>',

  // 浅色 / 深色主题
  'sun': '<circle cx="12" cy="12" r="4.4"/><path d="M12 3.4v2.2M12 18.4v2.2M20.6 12h-2.2M5.6 12H3.4M18.1 5.9l-1.6 1.6M7.5 16.5l-1.6 1.6M18.1 18.1l-1.6-1.6M7.5 7.5L5.9 5.9"/>',
  'moon': '<path d="M20.4 14.6A8.8 8.8 0 0 1 9.4 3.6a8.8 8.8 0 1 0 11 11z"/>',

  // 筛选（视频/作业过滤）
  'filter': '<path d="M3.6 5.4h16.8l-6.6 7.8v5.8l-3.6 2v-7.8z"/>',

  /* 方向箭头：面板里"回卡片流 ←"、翻卡、"去 OJ ↗"之外的纯方向动作 */
  'arrow-up': '<path d="M12 19.2V4.8"/><path d="M6.6 10.2L12 4.8l5.4 5.4"/>',
  'arrow-down': '<path d="M12 4.8v14.4"/><path d="M6.6 13.8L12 19.2l5.4-5.4"/>',
  'arrow-left': '<path d="M19.2 12H4.8"/><path d="M10.2 6.6L4.8 12l5.4 5.4"/>',
  'arrow-right': '<path d="M4.8 12h14.4"/><path d="M13.8 6.6L19.2 12l-5.4 5.4"/>',

  // 更多（⋯ 菜单）
  'dots': '<circle cx="5.4" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="18.6" cy="12" r="1.5" fill="currentColor" stroke="none"/>',

  // 读屏（👁 把前台内容读给助教）
  'eye': '<path d="M2.9 12S6.7 5.8 12 5.8 21.1 12 21.1 12 17.3 18.2 12 18.2 2.9 12 2.9 12z"/><circle cx="12" cy="12" r="3.1"/>',

  'lock': '<rect x="4.8" y="10.4" width="14.4" height="10" rx="2.6"/><path d="M8 10.4V8a4 4 0 0 1 8 0v2.4"/>',
  'user': '<circle cx="12" cy="8.4" r="4"/><path d="M4.8 20.4a7.2 7.2 0 0 1 14.4 0"/>',

  // 发送（助教输入框的回车键）
  'send': '<path d="M20.4 3.6L10.8 13.2"/><path d="M20.4 3.6l-6 16.8-3.6-7.2-7.2-3.6z"/>',

  'plus': '<path d="M12 5.2v13.6M5.2 12h13.6"/>',
  'minus': '<path d="M5.2 12h13.6"/>',

  'trash': '<path d="M4.4 7.2h15.2"/><path d="M9.4 4.2h5.2"/><path d="M6.4 7.2l.9 12.2a2.2 2.2 0 0 0 2.2 2h5a2.2 2.2 0 0 0 2.2-2l.9-12.2"/><path d="M10.2 10.8v6.4M13.8 10.8v6.4"/>',

  'database': '<ellipse cx="12" cy="6.4" rx="7.6" ry="2.8"/><path d="M4.4 6.4v11.2c0 1.6 3.4 2.9 7.6 2.9s7.6-1.3 7.6-2.9V6.4"/><path d="M4.4 12c0 1.6 3.4 2.9 7.6 2.9s7.6-1.3 7.6-2.9"/>',

  'layers': '<path d="M12 3.6L3.6 7.9l8.4 4.3 8.4-4.3z"/><path d="M3.6 11.9l8.4 4.3 8.4-4.3"/><path d="M3.6 15.9l8.4 4.3 8.4-4.3"/>',

  'cpu': '<rect x="6.6" y="6.6" width="10.8" height="10.8" rx="2.2"/><rect x="10" y="10" width="4" height="4" rx="1"/><path d="M12 3.4v3.2M12 17.4v3.2M3.4 12h3.2M17.4 12h3.2"/>',

  'wifi': '<path d="M3.8 9.2a13 13 0 0 1 16.4 0"/><path d="M6.9 12.7a8.7 8.7 0 0 1 10.2 0"/><path d="M10 16.2a4.2 4.2 0 0 1 4 0"/><circle cx="12" cy="19.4" r="1.15" fill="currentColor" stroke="none"/>',

  // 禁止（🚫 停用 / 不可用）
  'ban': '<circle cx="12" cy="12" r="8.4"/><path d="M5.9 5.9l12.2 12.2"/>',

  /* --------------------------------------------------- 补充：清单里出现的
     🔥 ⏳ 🔌 💬 ⌛ 这些没有直接列进需求清单，但界面上真出现过。 */

  // 连续天数（🔥 连续 N 天）
  'flame': '<path d="M12 20.4c3.3 0 5.8-2.3 5.8-5.4 0-4.2-3.9-6.3-4.6-11.4-1.9 1.7-2.7 3.9-2.6 5.6-1.4-.7-2-1.8-2.2-3.1-1.1 1.7-2.2 4.1-2.2 8.3 0 3.4 2.5 6 5.8 6z"/>',

  // 进行中（⏳ 正在抓取 / 核对）
  'hourglass': '<path d="M6.8 3.8h10.4M6.8 20.2h10.4"/><path d="M8.4 3.8c0 4.2 3.6 4.8 3.6 8.2s-3.6 4-3.6 8.2"/><path d="M15.6 3.8c0 4.2-3.6 4.8-3.6 8.2s3.6 4 3.6 8.2"/>',

  // 加载（配合 CSS 旋转；原本想用 ⏳，但转起来的东西应该用开口环）
  'loader': '<path d="M12 3.8a8.2 8.2 0 1 1-8.2 8.2"/>',

  // 测试连接（🔌）
  'plug': '<path d="M9.2 3.8v4.4M14.8 3.8v4.4"/><path d="M6.6 8.2h10.8v3.6a5.4 5.4 0 0 1-10.8 0z"/><path d="M12 17.2v2.6"/>',

  // 对话（💬 助教气泡的一句话版）
  'chat': '<path d="M20.4 15.2a2.2 2.2 0 0 1-2.2 2.2H8L4.4 21V6.6a2.2 2.2 0 0 1 2.2-2.2h11.6a2.2 2.2 0 0 1 2.2 2.2z"/>',

  // 编辑（改笔记/草稿）
  'edit': '<path d="M4.4 19.6l.8-3.6 9.6-9.6 2.8 2.8-9.6 9.6z"/><path d="M13.4 5.4l2.8 2.8"/>',

  // 帮助
  'help': '<circle cx="12" cy="12" r="8.4"/><path d="M9.6 9.4a2.6 2.6 0 0 1 5 .9c0 1.8-2.6 2.2-2.6 3.9"/><circle cx="12" cy="17" r="1.05" fill="currentColor" stroke="none"/>',

  // 首页 / 回到开头
  'home': '<path d="M3.8 10.4L12 3.8l8.2 6.6v8.4a1.8 1.8 0 0 1-1.8 1.8h-3.6v-6h-5.6v6H5.6a1.8 1.8 0 0 1-1.8-1.8z"/>',

  // 云（同步/在线状态）
  'cloud': '<path d="M7.6 18.4h9.6a3.9 3.9 0 0 0 .6-7.7 5.6 5.6 0 0 0-10.9-1 4.4 4.4 0 0 0 .7 8.7z"/>'
};

/* ============================================================================
   外壳：只在这里拼一次。
   stroke-width 交给 CSS（.ico 里是 1.8）也能生效，但这里写死一份是为了预览页/单独
   拷出来给别处用时也能立即可用；CSS 里再覆盖就按 CSS 走（内联属性优先级低于 CSS
   的 presentation attribute 规则 —— 实际上内联属性会被 CSS 覆盖，正好留着可调）。
   ============================================================================ */
function icon(name, cls){
  var p = ICONS[name];
  // 未知名字返回空串：界面重试/半截图状态下少一个图标可以接受，抛错白屏不行。
  if (!p) return '';
  return '<svg class="ico' + (cls ? ' ' + cls : '') + '" viewBox="0 0 24 24" fill="none"' +
         ' stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"' +
         ' aria-hidden="true">' + p + '</svg>';
}

// 给需要"有没有这个图标"的调用方用（比如自检脚本、预览页）
function hasIcon(name){ return !!ICONS[name]; }

/* ============================================================================
   emoji → 图标名
   ----------------------------------------------------------------------------
   只用于 **UI 控件** 上的 emoji。正文里的 emoji（markdown 原文、AI 回复、题面、
   解析、代码注释）一律不动 —— 那是内容，不是图标。
   带变体选择符 FE0F 的形式（⚠️）和裸形式（⚠）都列了，因为源文件里两种都出现过。
   ============================================================================ */
var IEMOJI = {
  // 面板标题 / 图标栏
  '📋': 'copy', '🧪': 'test-tube', '📝': 'homework', '⚙️': 'settings', '⚙': 'settings',
  '🔍': 'search', '🔎': 'search', '🔄': 'refresh', '🔁': 'refresh', '📅': 'calendar',
  '📺': 'film', '🎬': 'film', '📖': 'book', '📚': 'book', '📄': 'document',
  '🖼': 'image', '🖼️': 'image', '🔗': 'link', '📌': 'pin', '🎯': 'target',
  '🏁': 'flag', '🚀': 'rocket', '🤖': 'robot', '🧹': 'broom', '✨': 'sparkle',
  '💡': 'lightbulb', '⚠️': 'warning', '⚠': 'warning', '✅': 'check', '❌': 'cross',
  '⏹': 'stop', '⏹️': 'stop', '▶': 'play', '▶️': 'play', '⏳': 'hourglass',
  '🔥': 'flame', '🐍': 'python', '💰': 'wallet', '👁': 'eye', '👁️': 'eye',
  '🔑': 'key', '🔌': 'plug', '📤': 'upload', '⬇': 'download', '⬇️': 'download',
  '💬': 'chat', '💭': 'lightbulb', '📭': 'inbox', '🎉': 'sparkle', '⏰': 'clock',
  '⌛': 'hourglass', '☰': 'menu', '✕': 'close',
  '‹': 'chevron-left', '›': 'chevron-right', '▾': 'chevron-down', '▴': 'chevron-up',
  '⤢': 'expand', '↗': 'external-link',
  // 带变体选择符 FE0F 的写法（源文件里两种都有，替换时才能全都抓到）
  '🖼️': 'image', '⏹️': 'stop', '▶️': 'play', '👁️': 'eye', '⬇️': 'download',
  '📭️': 'inbox', '⌛': 'hourglass', '🚫': 'ban', '🔎': 'search'
};

// 预览页/自检脚本可读的清单（顺序＝上面的书写顺序）
var ICON_NAMES = [];
for (var _k in ICONS) ICON_NAMES.push(_k);

/* 把一段 UI 文本里的 emoji 换成对应图标。
   可选用法（Lead 改 web/index.html 时用得上）：
     btn.innerHTML = emojiToIcon('🧪 用样例测');       // → '<svg …> 用样例测'
     hwGroupHead.innerHTML = emojiToIcon('📝 作业');
   注意：**不要**把它套在正文渲染上（md()、AI 回复、题面）—— 那里的 emoji 是内容。
   未知 emoji 原样留下，所以"套了也没替换"的地方会很明显，方便查漏。 */
function emojiToIcon(text){
  if (text == null) return '';
  var s = String(text), out = '', i = 0;
  // 逐个字符扫：不能直接用 replace(/[emoji]/g)，因为 ⚠️ 是 字符+FE0F 两个码位，
  // 必须先试"两码位"再试"单码位"，否则 📭️ 这类会被拆成两个。
  while (i < s.length){
    var two = s.substr(i, 2), one = s.charAt(i);
    if (IEMOJI[two]){ out += icon(IEMOJI[two]); i += 2; continue; }
    if (IEMOJI[one]){ out += icon(IEMOJI[one]); i += 1; continue; }
    out += one; i += 1;
  }
  return out;
}

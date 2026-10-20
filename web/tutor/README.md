# web/tutor/ —— 占位说明（代理 D 写，只占位不实现）

这个目录按 SPEC 第 2 节留给**桌面壳（代理 C）在启动时挂载可视化引擎**用。

- 真正的可视化引擎在 `D:\opencode\tools\pytutor\`（`viewer.html` 等），**那个目录只读，不要改**。
- 卡片流界面（`web/index.html`）里的「▶ 在可视化里跑这段」按钮，会跳到：

  ```
  /tutor?code=<urlencoded 代码>
  ```

  这个路由由 `app/main.py` 提供：它读 `tools/pytutor/viewer.html` 返回，
  并负责把 `?code=` 里的代码**预填进可视化的代码框**（具体方案见 SPEC 7.1）。

- 所以这个目录**现在是空的**，不放任何文件逻辑，也不需要 `index.html`。
  如果打包时 `--add-data "..\web;web"` 需要一个真实存在的目录，本文件即可满足。

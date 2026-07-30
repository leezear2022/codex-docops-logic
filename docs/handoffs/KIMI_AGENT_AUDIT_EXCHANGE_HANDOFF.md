# Handoff: cross-agent document exchange and audit protocol

- author: Kimi Code
- auditor: Codex
- branch: feat/exchange-audit
- implementation commit: b9f6a5807549b30e3341f1268f8ab600a0fab409
- base commit: 560b51d (main, feat: harden phase 1 plugin workflow)
- handoff commit: (this document, see git log)

## 方案摘要

在 Codex 插件仓库中实现了一个宿主中立的异步文档协议:一个编码代理
(executor,首要场景为 Codex)完成任务后产出结构化交付文档,另一个代理
(auditor,首要场景为 Kimi Code)审计真实代码与证据后产出结构化审计报告,
executor 对 findings 逐条接受或附证据异议,然后开启新一轮。所有历史落在
`.docops/exchange/<task-id>/`,按 round 分目录,物理上不可覆盖。

Kimi Code 不需要任何插件 API:读 `templates/kimi-auditor.md` + exchange 文档 +
运行 `scripts/dol.py`(纯 Python 标准库)即可完整参与。

## 设计决定

1. **JSON sidecar + Markdown 双文件**:结构化字段全部在 `*.json`
   (stdlib `json` 可靠读写),Markdown 只承载人读叙述。不引入任何 YAML
   解析需求,中文正文零风险。
2. **round 目录即不可变单元**:`rNNN/` 每轮一个目录,每类文档每轮至多一份
   (delivery/audit/response),重复写入直接被 CLI 拒绝;没有 `--force`。
3. **disputed 不允许直接复审同一份 audit**:executor 异议后必须以一次新的
   `deliver`(可引用异议证据、commit 可不变)开启新 round,audit 再作用于新
   round。这样保持"每轮 ≤1 delivery/audit/response"的不变量,append-only 绝对
   纯净。这是与原设想的偏差,属于有意的简化。
4. **approve 强制要求 delivery.validation 非空**:不允许"口头通过";
   `request_changes` 强制要求至少一条 finding(含 severity|path|evidence|advice)。
5. **锁文件而非 flock**:`.lock` 用 `O_CREAT|O_EXCL` 创建,存在即报可操作错误,
   跨平台可移植,两个代理近同时写入时后写者得到明确冲突提示。
6. **exchange 不写 ev.jsonl**:避免改动现有事件 schema 契约;exchange 文档本身
   即完整历史。`exchange` 也不要求先 `dol init`,任何仓库可用。
7. **commit 字段语义**:`base_commit`/`result_commit` 为空字符串表示"未记录"
   ——推荐证据,非必填;README 与 schema description 均已写明。

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `scripts/dol.py` | +750 行:exchange 数据模型、TRANSITIONS、锁、原子写、9 个子命令、`validate_exchange` |
| `templates/exchange-request.md` | 任务请求模板 |
| `templates/exchange-delivery.md` | executor 交付模板 |
| `templates/exchange-audit.md` | 审计报告模板 |
| `templates/exchange-response.md` | findings 回复模板 |
| `templates/exchange-closure.md` | 关闭文档模板 |
| `templates/kimi-auditor.md` | 可复制到目标仓库的 Kimi 审计说明 |
| `schemas/exchange.schema.json` | state 与 5 类 sidecar 的 JSON Schema(draft 2020-12) |
| `skills/xchange/SKILL.md` | Codex 侧 skill `docops-exchange` |
| `tests/test_exchange.py` | 14 项新测试(stdlib unittest) |
| `README.md` | exchange 章节:完整示例 + 4 条说明 |

## CLI 示例

```bash
DOL="<plugin-root>/scripts/dol.py"
python3 "$DOL" exchange new --id rpc-7004 --title "Fix RPC timeout" \
  --from user --to codex --acc "timeout retried" --base-commit abc123
python3 "$DOL" exchange start rpc-7004
python3 "$DOL" exchange deliver rpc-7004 --result-commit def456 \
  --files src/rpc.py --claims "bounded retry" \
  --va "python3 -m unittest discover -s tests=pass"
python3 "$DOL" exchange audit-start rpc-7004
python3 "$DOL" exchange audit-submit rpc-7004 --verdict request_changes \
  --finding "major|src/rpc.py:88|retry unbounded|cap at 3"
python3 "$DOL" exchange respond rpc-7004 --finding F1 --action accept --note "capped in def789"
python3 "$DOL" exchange deliver rpc-7004 ...   # round 2
python3 "$DOL" exchange audit-start rpc-7004
python3 "$DOL" exchange audit-submit rpc-7004 --verdict approve
python3 "$DOL" exchange close rpc-7004
python3 "$DOL" exchange status rpc-7004
python3 "$DOL" exchange validate --all
```

## 状态机

```
requested ──start──▶ in_progress ──deliver──▶ ready_for_audit ──audit-start──▶ auditing
auditing ──submit approve──────────▶ approved ──close──▶ closed
auditing ──submit request_changes──▶ changes_requested
changes_requested ──respond accept──▶ changes_requested (response 文档追加)
changes_requested ──respond dispute─▶ disputed
changes_requested|disputed ──deliver(新 round)──▶ ready_for_audit
requested|in_progress ──close──▶ closed (resolution=cancelled)
closed: 终态
```

非法转换返回 `{"ok":false,"miss":["status:<current>"],"fix":["allowed targets ..."]}`,exit 1。

## 测试命令和真实结果

```bash
python3 -m unittest discover -s tests      # Ran 32 tests in 0.370s — OK
python3 -m py_compile scripts/*.py hooks/*.py   # 通过
git diff --check                           # 通过
python3 scripts/dol.py exchange validate --all  # 冒烟仓库 {"ok":true,"errors":[],"tasks":1}
```

32 = 原 18 项(全部继续通过)+ 新 14 项:happy path、changes_requested→respond→
新 round→approved、disputed、非法转换、重复任务/锁冲突、路径穿越(5 种 id)、
缺 delivery 禁 audit、无证据禁 approve、request_changes 必须有 finding、未知
finding 拒答、篡改检测、schema↔validator 契约一致、中文标题与正文、status 列表。
另做了 README 示例逐条的临时目录端到端冒烟(见上方 CLI 示例),全链路通过。

## 已知限制

- 无 stale lock 自动回收:崩溃遗留 `.lock` 需人工删除(错误信息已说明)。
- `exchange validate` 校验文档间一致性,但不重放状态机历史(无事件日志,
  篡改 state.json 的 status 只能被部分规则捕获,如 approved 必须有对应
  approve audit)。
- respond 追加条目会重写同 round 的 response.json/md(同文档内只增不改,
  doc id 不变,不破坏跨轮 append-only)。
- exchange 事件不进入 `.docops/ev.jsonl`,与 learn/prom 等现有机制无联动。
- 字段值 >8KB 截断,不防"把密钥塞进 --note"这类主动误用(文档已告诫)。

## 我最不确定的三个地方

1. **disputed 必须经新 round 复审**是否符合你对"请求下一轮审计"的预期——
   它要求 executor 多写一份 delivery,即使代码未变。
2. **approve 强制 validation 非空**是否过严:有些任务(纯文档)没有自然
   的验证命令,目前只能 `--va "manual review=pass"` 之类的自律记录。
3. **锁的粒度**:整个 task 一把锁,respond 连续调用也走锁;极端并发下
   后写者直接失败而非排队,是否符合"可检测冲突"的预期强度。

## 希望 Codex 重点审计的内容

- `scripts/dol.py` 中 `validate_exchange` 的规则覆盖度:是否存在能通过
  validate 但语义损坏的状态(重点:status 与各 round 文档的一致性规则)。
- `task_lock`/`write_file_atomic` 的竞态与异常路径(lock 泄漏、tmp 残留)。
- `doc_sidecar`/`task_path` 的路径安全:是否有未覆盖的穿越或 id 混淆。
- TRANSITIONS 表是否符合任务书的全部强制规则(审计不早于交付、approved
  对应明确轮次、changes_requested 后必须有 response 或新 delivery)。
- `schemas/exchange.schema.json` 与 `EXCHANGE_REQUIRED` 的镜像是否完备,
  契约测试是否真的防回归。
- README 示例与 `templates/kimi-auditor.md` 的命令是否与实际 CLI 一致。

---

## Round 2: fixes for Codex audit (request_changes, 5 major findings)

Round-1 handoff is above, unchanged. This section is appended after the Codex
audit; the fixes live in a follow-up commit on the same branch.

- **F1 (approve gates) — fixed.** `audit-submit --verdict approve` now rejects
  any `fail`/`mix` validation entry and any `blocker`/`major` finding (minor/
  info allowed). New validation result `not_applicable` for steps that
  genuinely do not apply (reason goes in the cmd text), per the auditor's
  suggestion; the approval gate itself stays.
- **F2 (per-finding closure) — fixed.** `respond` requires a non-empty
  `--note`; each finding accepts exactly one response; `deliver` refuses a new
  round while any finding of the current audit is unanswered (error lists the
  missing finding ids).
- **F3 (validate robustness) — fixed.** `validate` now: flags orphan task
  directories without `state.json`; cross-checks disk sidecars against the
  state index in both directions; verifies `md_sha256` so Markdown edits after
  writing are detected; type-guards every field (a non-integer `round`
  produces a structured error, never a traceback); enforces per-status
  invariants (`requested` must be round 0; `ready_for_audit` and beyond
  require a delivery in the current round; approve-consistency rules mirror
  the new F1 gates).
- **F4 (append-only responses) — fixed.** Responses are now one immutable
  document per finding: `rNNN/response-F<n>.json/.md`. No in-place rewrites
  remain anywhere in the protocol; JSON+MD are both written atomically and any
  crash between them is caught by validate (missing counterpart / hash
  mismatch).
- **F5 (plugin version) — partially fixed.** `plugin.json` bumped to
  `0.2.0+codex.20260718140000`. Per the task constraints the installed plugin
  cache under `~/.codex` / marketplaces was **not** touched; the user must
  re-run `codex plugin add docops-logic@personal` (and re-trust hooks) for the
  installed copy to expose `docops-exchange`.

Contract updates: `schemas/exchange.schema.json` mirrors the new
`EXCHANGE_REQUIRED` (incl. `md_sha256`) and the `not_applicable` enum; the
schema↔validator contract test covers this. `templates/exchange-response.md`,
`templates/kimi-auditor.md`, `skills/xchange/SKILL.md`, and README notes were
updated to the new rules.

Verification on the fix commit:

- `python3 -m unittest discover -s tests`: **Ran 40 tests — OK** (18 legacy +
  22 exchange; 8 new tests for F1–F3 gates and tamper detection)
- `python3 -m py_compile scripts/*.py hooks/*.py`: OK
- `git diff --check`: OK
- End-to-end smoke: unanswered finding blocks round 2 with `miss:["F2"]`;
  tampered `request.md` fails validate with "markdown hash mismatch";
  per-finding `response-F1/F2` documents are immutable and validated.

Open for re-audit:

- Whether `not_applicable` should carry a separate structured `reason` field
  instead of embedding the reason in `cmd` (kept simple for now).
- Crash between the JSON and Markdown atomic writes is detectable but not
  self-healing (documented limitation).
- Installed-plugin refresh (F5) is a user action; not verifiable from this
  repo.

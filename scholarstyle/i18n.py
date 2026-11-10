"""Small explicit UI catalogue. Source text and manuscript contents are never translated."""
import re
from string import Formatter

LANGUAGES = {'zh': '中文', 'en': 'English', 'de': 'Deutsch'}
# Chinese source | English | German. Named fields preserve user text verbatim.
_DATA = r'''
勾选论文后点击训练，自动下载并入库。|Select papers, then click Train to download and import automatically.|Arbeiten auswählen und Trainieren klicken: Download und Import erfolgen automatisch.
冻结档案保存路径|Frozen profile save path|Speicherpfad des eingefrorenen Profils
上传文件与训练文献|Upload files & training papers|Dateien & Trainingsliteratur
网页搜索论文|Search papers online|Literatur online suchen
查找作者与论文|Find authors and papers|Autoren und Literatur suchen
语言|Language|Sprache
界面风格|Appearance|Darstellung
ScholarStyle Studio · 科研论文风格工作室|ScholarStyle Studio · Scientific writing|ScholarStyle Studio · Wissenschaftliches Schreiben
让科学表达更接近你的研究团队  ·  本地学习  /  透明修改  /  可复用风格档案|Scientific writing in your team's style · Local learning / Transparent revisions / Reusable style profiles|Wissenschaftlich schreiben im Stil Ihres Teams · Lokal lernen / Änderungen vergleichen / Stilprofile wiederverwenden
01  文献库与风格训练|01  Papers & style training|01  Literatur & Stiltraining
支持 DOCX、文本型 PDF，单文件最大 512 MB。已入库论文会保留；每次训练使用当前勾选的全部论文。|Import DOCX or text PDFs, up to 512 MB per file. Training uses all checked papers; the library is retained.|DOCX oder Text-PDF importieren, bis zu 512 MB pro Datei. Das Training verwendet alle markierten Arbeiten; die Bibliothek bleibt erhalten.
＋ 导入论文|＋ Import papers|＋ Arbeiten importieren
全选|Select all|Alle auswählen
移除勾选|Remove checked|Markierte entfernen
作者 / 研究团队名称|Author / research team name|Name des Autors / Forschungsteams
风格名称|Style name|Stilname
用本地 LLM 学习写作规则|Learn style rules with local LLM|Stilregeln mit lokalem LLM lernen
训练 / 更新并冻结|Train / update & freeze|Trainieren / aktualisieren & einfrieren
冻结的是风格规则、统计和全文检索库，不是微调后的 LLM 权重。关闭 LLM 学习可离线建立统计与检索档案。|The frozen profile contains style rules, statistics and searchable text, not fine-tuned LLM weights. Disable LLM learning for offline statistics and indexing.|Das eingefrorene Profil enthält Stilregeln, Statistiken und durchsuchbare Texte, keine feinabgestimmten LLM-Gewichte. Ohne LLM werden Statistik und Index offline erstellt.
① 文献与训练|① Papers & training|① Literatur & Training
查找作者与论文|Find authors & papers|02  Autoren & Arbeiten suchen
先根据机构 / ORCID 区分同名作者，再选择论文。仅下载公开全文；检索不会上传你的本地论文或草稿。|Identify the author by institution / ORCID, then choose papers. Only public full texts are downloaded; local papers and drafts are never uploaded for search.|Autoren anhand von Institution / ORCID identifizieren, dann Arbeiten auswählen. Nur öffentlich zugängliche Volltexte werden geladen; lokale Texte werden nicht zur Suche hochgeladen.
作者姓名，例如：First Last|Author name, e.g. First Last|Autorenname, z. B. Vorname Nachname
搜索作者|Search authors|Autoren suchen
最多检索篇数|Maximum papers|Maximale Anzahl
检索选中作者的论文|Find selected author's papers|Arbeiten des gewählten Autors suchen
全选可下载论文|Select downloadable papers|Herunterladbare Arbeiten auswählen
下载勾选论文并入库|Download checked papers|Markierte Arbeiten herunterladen
② 作者检索|② Author search|② Autorensuche
02  草稿修改与对比|02  Draft revision & comparison|02  Entwurf überarbeiten & vergleichen
导入草稿|Import draft|Entwurf importieren
恢复上次结果|Restore last results|Letzte Ergebnisse wiederherstellen
原始草稿 · 可直接粘贴或编辑|Original draft · Paste or edit text|Originalentwurf · Text einfügen oder bearbeiten
在这里粘贴科学论文 draft，或导入 DOCX / PDF…|Paste your scientific draft here, or import DOCX / PDF…|Wissenschaftlichen Entwurf hier einfügen oder DOCX / PDF importieren…
额外要求：例如 保留术语、加强段落衔接、使用英式英语|Instructions: preserve terminology, improve transitions, use British English…|Vorgaben: Fachbegriffe beibehalten, Übergänge verbessern, britisches Englisch…
使用模型 + 冻结风格修改|Revise with model + frozen style|Mit Modell + Stilprofil überarbeiten
导出为重新排版的文本型 Word；不保留原文图片、公式对象、复杂表格、脚注或参考文献管理器字段。|Exports a newly formatted text-only Word file; original images, equation objects, complex tables, footnotes and citation-manager fields are not retained.|Export als neu formatierte Word-Textdatei; Bilder, Formelobjekte, komplexe Tabellen, Fußnoten und Literaturverwaltungsfelder werden nicht übernommen.
修改会话 · 绿色新增 / 红色删除|Revision review · Green: added / Red: removed|Änderungsansicht · Grün: ergänzt / Rot: entfernt
选中段块后可在此手动调整修改稿，然后点击「保存并确认」。|Select a section, edit the revision here, then save and approve.|Abschnitt wählen, Überarbeitung hier bearbeiten und anschließend speichern und bestätigen.
保存并确认本段|Save & approve section|Abschnitt bestätigen
本段保留原文|Keep original section|Original beibehalten
确认无警告段落|Approve unflagged sections|Unauffällige bestätigen
导出干净 Word|Export clean Word|Word ohne Markierungen
导出彩色对比 Word|Export comparison Word|Word mit Änderungen
② 草稿工作室|② Draft studio|② Entwurfsstudio
04  本地模型与设置|04  Local models & settings|04  Lokale Modelle & Einstellungen
选择预设或已安装模型，也可输入模型名称。此选择直接用于第三步草稿修改和第一步风格学习。|Choose a preset or installed model, or enter a model tag. This selection powers draft revision in step 3 and style learning in step 1.|Voreinstellung oder installiertes Modell wählen, oder Modellnamen eingeben. Diese Auswahl wird für Entwurfsrevision in Schritt 3 und Stiltraining in Schritt 1 verwendet.
Ollama 地址|Ollama endpoint|Ollama-Adresse
本地模型|Local model|Lokales Modell
可选，仅用于 OpenAlex 检索；不保存到磁盘|Optional: OpenAlex search only; never saved to disk|Optional: nur für OpenAlex-Suche; wird nicht gespeichert
检查已安装模型|Refresh installed models|Installierte Modelle aktualisieren
下载 / 准备选中模型|Download / prepare model|Modell laden / vorbereiten
安装 / 更新 Ollama|Install / update Ollama|Ollama installieren / aktualisieren
测试选中模型|Test selected model|Ausgewähltes Modell testen
取消在当前文档页 / 请求完成后生效。本地模型单次请求最长等待 10 分钟。自动检查不能保证科学含义完全不变，请审阅后导出。|Cancellation takes effect between pages / requests. Model requests can take up to 10 minutes. Review scientific meaning before export.|Abbruch erfolgt zwischen Seiten / Anfragen. Modellanfragen können bis zu 10 Minuten dauern. Wissenschaftliche Bedeutung vor dem Export prüfen.
④ 本地模型|④ Local models|④ Lokale Modelle
就绪 · 添加导师论文，然后训练并冻结风格档案。|Ready · Add reference papers, then train and freeze a style profile.|Bereit · Referenzarbeiten hinzufügen, dann ein Stilprofil trainieren und einfrieren.
取消任务|Cancel task|Aufgabe abbrechen
任务完成|Task completed|Aufgabe abgeschlossen
正在取消… 等待当前读取 / 模型请求结束。|Cancelling… Waiting for the current read / model request.|Abbruch läuft… Aktuellen Lesevorgang / Modellanfrage abwarten.
任务未完成 · {message}|Task incomplete · {message}|Aufgabe unvollständig · {message}
如为连接错误，请检查 Ollama 是否启动，以及模型是否已下载。|For connection errors, check that Ollama is running and the model is downloaded.|Bei Verbindungsfehlern prüfen, ob Ollama läuft und das Modell heruntergeladen wurde.
尚未训练。导入文献后点击「训练 / 更新并冻结」。|No style profile yet. Import papers, then train / update and freeze.|Noch kein Stilprofil. Arbeiten importieren, dann trainieren / aktualisieren und einfrieren.
档案读取失败：{error}|Could not read profile: {error}|Profil konnte nicht gelesen werden: {error}
选择已发表论文|Select published papers|Veröffentlichte Arbeiten auswählen
导入已取消；已入库文献保留。|Import cancelled; imported papers are retained.|Import abgebrochen; bereits importierte Arbeiten bleiben erhalten.
新增 {count} 篇；相同文本自动去重。|Added {count} papers; duplicate text is skipped automatically.|{count} Arbeiten hinzugefügt; identische Texte werden automatisch übersprungen.
导入结果|Import results|Importergebnis
机构未知|Unknown institution|Institution unbekannt
未找到作者，请尝试全名或其他拼写。|No authors found. Try the full name or a different spelling.|Keine Autoren gefunden. Vollständigen Namen oder andere Schreibweise versuchen.
请先选择正确的作者。|Select the correct author first.|Zuerst den richtigen Autor auswählen.
仅元数据|Metadata only|Nur Metadaten
找到 {count} 篇。仅有全文的论文可以学习；摘要不会冒充全文。|Found {count} papers. Only full texts are used for learning; abstracts are not treated as full papers.|{count} Arbeiten gefunden. Nur Volltexte werden zum Lernen verwendet; Abstracts gelten nicht als vollständige Arbeiten.
请勾选需要导入的论文。|Check the papers to import.|Zu importierende Arbeiten markieren.
已安装模型：|Installed models:|Installierte Modelle:
选择草稿|Select draft|Entwurf auswählen
请先训练冻结风格模型。|Train and freeze a style profile first.|Zuerst ein Stilprofil trainieren und einfrieren.
请先导入或粘贴论文草稿（至少 50 字符）。|Import or paste a draft first (at least 50 characters).|Zuerst einen Entwurf importieren oder einfügen (mindestens 50 Zeichen).
已确认|Approved|Bestätigt
待审阅|Needs review|Zu prüfen
 · ⚠ 请核对| · ⚠ Check carefully| · ⚠ Bitte prüfen
段块 {number} · {state}|Section {number} · {state}|Abschnitt {number} · {state}
修改对比|Revision comparison|Änderungsvergleich
修改说明|Explanation|Erläuterung
需要核对|Review required|Prüfung erforderlich
风格参考（检索相关性不等于质量评分）|Style references (retrieval relevance is not a quality score)|Stilreferenzen (Suchrelevanz ist keine Qualitätsbewertung)
修改稿不能为空。|The revision cannot be empty.|Die Überarbeitung darf nicht leer sein.
已恢复完整结果。|Complete results restored.|Vollständige Ergebnisse wiederhergestellt.
已恢复部分结果；任务未完成，不能导出完整论文。请重新运行草稿修改。|Partial results restored. The task is incomplete; rerun revision before exporting the full manuscript.|Teilergebnisse wiederhergestellt. Aufgabe unvollständig; vor dem Export des gesamten Manuskripts erneut überarbeiten.
尚无完整修改结果。请先完成全文修改。|No complete revision yet. Finish revising the full draft first.|Noch keine vollständige Überarbeitung. Zuerst den gesamten Entwurf überarbeiten.
请先确认各段修改。有警告的段落需要逐段审阅。|Approve all sections first. Flagged sections require individual review.|Zuerst alle Abschnitte bestätigen. Markierte Abschnitte einzeln prüfen.
保存 Word|Save Word|Word speichern
已导出|Exported|Exportiert
正在取消后台任务，结束后可关闭窗口。|Cancelling the background task. Close the window after it finishes.|Hintergrundaufgabe wird abgebrochen. Fenster anschließend schließen.
数据目录：{path}|Data directory: {path}|Datenverzeichnis: {path}
{title}   ·   {count} 字符|{title}   ·   {count} characters|{title}   ·   {count} Zeichen
冻结模型：{name}  ·  v{version}  ·  {papers} 篇 / {chunks} 段块|Frozen profile: {name} · v{version} · {papers} papers / {chunks} sections|Stilprofil: {name} · v{version} · {papers} Arbeiten / {chunks} Abschnitte
平均句长：{length} 词  ·  方法：{method}|Mean sentence length: {length} words · Method: {method}|Mittlere Satzlänge: {length} Wörter · Methode: {method}
草稿使用模型|Draft editing model|Modell für Entwurfsrevision
管理 / 下载模型|Manage / download models|Modelle verwalten / laden
首次运行会自动准备所选模型。界面语言只控制菜单和修改说明，论文正文保留原语言。|First use prepares the selected model automatically. Interface language controls menus and revision explanations; manuscript language is preserved.|Beim ersten Einsatz wird das gewählte Modell automatisch vorbereitet. Die Oberflächensprache gilt für Menüs und Erläuterungen; die Manuskriptsprache bleibt erhalten.
尚无冻结风格档案|No frozen style profile|Kein eingefrorenes Stilprofil
当前流程：{model} + {profile} → 草稿修改|Active workflow: {model} + {profile} → draft revision|Aktiver Ablauf: {model} + {profile} → Entwurfsrevision
未检查|Not checked|Nicht geprüft
已安装|Installed|Installiert
需要下载|Download required|Download erforderlich
模型状态：{status}|Model status: {status}|Modellstatus: {status}
自定义本地模型；请确认模型支持文本与结构化输出。|Custom local model; verify text and structured-output support.|Benutzerdefiniertes lokales Modell; Text und strukturierte Ausgabe prüfen.
轻量模型，适合先测试流程；复杂科学表达需要仔细审阅。|Smaller model for initial testing; review complex scientific phrasing carefully.|Kleineres Modell zum Testen; komplexe wissenschaftliche Formulierungen sorgfältig prüfen.
均衡文本模型；适用于本地风格学习和草稿修改。|Balanced text model for local style learning and draft revision.|Ausgewogenes Textmodell für lokales Stiltraining und Entwurfsrevision.
较大模型；需要更多内存，CPU 推理可能较慢。|Larger model; requires more memory and may run slowly on CPU.|Größeres Modell; benötigt mehr Speicher und kann auf CPU langsam sein.
安装 / 更新会使用官方安装程序，可能重启 Ollama。已有模型保留；首次下载需要联网。|Install / update uses the official installer and may restart Ollama. Existing models are retained; initial downloads require internet access.|Installation / Update verwendet den offiziellen Installer und startet Ollama ggf. neu. Vorhandene Modelle bleiben erhalten; Downloads benötigen Internet.
选中模型已准备好：{model}|Selected model is ready: {model}|Ausgewähltes Modell ist bereit: {model}
模型响应测试通过：{model}\n{response}|Model response test passed: {model}\n{response}|Modellantwort erfolgreich getestet: {model}\n{response}
正在检查本机 Ollama 和选中模型…|Checking local Ollama and selected model…|Lokales Ollama und ausgewähltes Modell werden geprüft…
正在启动本机 Ollama…|Starting local Ollama…|Lokales Ollama wird gestartet…
正在下载模型：{model}|Downloading model: {model}|Modell wird heruntergeladen: {model}
正在测试选中模型的短文本响应…|Testing the selected model with a short prompt…|Ausgewähltes Modell wird mit einem kurzen Prompt getestet…
任务已取消|Task cancelled|Aufgabe abgebrochen
下载已取消|Download cancelled|Download abgebrochen
模型已下载：{model}|Model downloaded: {model}|Modell heruntergeladen: {model}
选中模型尚未安装。请先下载模型。|Selected model is not installed. Download it first.|Ausgewähltes Modell ist nicht installiert. Zuerst herunterladen.
未安装 Ollama。请点击「下载 / 准备选中模型」。|Ollama is not installed. Click Download / prepare model.|Ollama ist nicht installiert. Auf Modell laden / vorbereiten klicken.
自动安装 / 更新仅支持默认本机端口 11434。|Automatic installation / updates require the default local port 11434.|Automatische Installation / Updates erfordern den lokalen Standardport 11434.
无法连接自定义本机服务。请手动启动该地址的 Ollama。|Cannot connect to the custom local endpoint. Start Ollama at that address manually.|Benutzerdefinierte lokale Adresse nicht erreichbar. Ollama dort manuell starten.
下载结束后未找到选中模型，请重试。|Selected model was not found after download. Please retry.|Ausgewähltes Modell nach Download nicht gefunden. Bitte erneut versuchen.
选中模型未返回完整响应，请检查内存和模型兼容性。|The selected model returned no complete response. Check memory and compatibility.|Das ausgewählte Modell lieferte keine vollständige Antwort. Speicher und Kompatibilität prüfen.
Ollama 启动失败。请查看 ~/.ollama/logs/scholarstyle-startup.log。|Ollama failed to start. See ~/.ollama/logs/scholarstyle-startup.log.|Ollama konnte nicht starten. Siehe ~/.ollama/logs/scholarstyle-startup.log.
数值/统计量发生变化，请核对。|Numbers / statistics changed; verify them.|Zahlen / Statistiken wurden geändert; bitte prüfen.
引用标记可能发生变化，请核对。|Citation markers may have changed; verify them.|Zitationsmarkierungen könnten verändert sein; bitte prüfen.
否定、谨慎措辞或显著性表述有变化。|Negation, hedging or significance wording changed.|Verneinung, vorsichtige Formulierung oder Signifikanzangaben wurden verändert.
段落长度变化较大，可能遗漏内容或增加论断。|Large length change: content may be missing or claims added.|Starke Längenänderung: Inhalte könnten fehlen oder Aussagen hinzugefügt worden sein.
修改稿出现与参考论文连续 8 词以上相同的新措辞，请检查是否照搬句子或引入参考论文结论。|The revision introduces 8 or more consecutive words from a reference. Check for copied phrasing or transferred claims.|Die Überarbeitung enthält mindestens 8 aufeinanderfolgende Wörter aus einer Referenz. Auf übernommene Formulierungen oder Aussagen prüfen.
本地修改 · {current}/{total} 段块|Local revision · section {current}/{total}|Lokale Überarbeitung · Abschnitt {current}/{total}
学习 {current}/{total} · {title} · 段块 {part}|Learning {current}/{total} · {title} · section {part}|Lernen {current}/{total} · {title} · Abschnitt {part}
读取 {title} · 第 {page}/{total} 页|Reading {title} · page {page}/{total}|Lesen: {title} · Seite {page}/{total}
已检索 {count} 篇论文|Found {count} papers|{count} Arbeiten gefunden
下载论文 · {size} MB|Downloading paper · {size} MB|Arbeit wird geladen · {size} MB
下载：{title}|Downloading: {title}|Download: {title}
请先勾选训练论文。|Select papers for training first.|Zuerst Arbeiten für das Training markieren.
训练已取消，原冻结模型保留。|Training cancelled; the previous frozen profile is retained.|Training abgebrochen; bisheriges Stilprofil bleibt erhalten.
修改已取消，已完成段落保存在恢复文件中。|Revision cancelled; completed sections are saved for recovery.|Überarbeitung abgebrochen; fertige Abschnitte sind zur Wiederherstellung gespeichert.
修改已取消，结果尚未标记为完成。|Revision cancelled; results are not marked complete.|Überarbeitung abgebrochen; Ergebnisse gelten nicht als vollständig.
模型返回空修改结果。已完成内容保存在恢复文件中。|Model returned an empty revision. Completed sections are saved for recovery.|Modell lieferte eine leere Überarbeitung. Fertige Abschnitte sind gespeichert.
模型返回格式不正确，请重试。|Invalid model response format. Please retry.|Ungültiges Antwortformat des Modells. Bitte erneut versuchen.
模型未返回 JSON 对象，请重试。|Model did not return a JSON object. Please retry.|Modell lieferte kein JSON-Objekt. Bitte erneut versuchen.
仅允许本机 Ollama 地址。|Only local Ollama endpoints are allowed.|Nur lokale Ollama-Adressen sind erlaubt.
请输入本地模型名称；不支持云端模型或远程模型路径。|Enter a local model tag; cloud models and remote model paths are not supported.|Lokalen Modellnamen eingeben; Cloud-Modelle und entfernte Modellpfade werden nicht unterstützt.
请输入本机 Ollama 根地址，例如 http://127.0.0.1:11434|Enter the local Ollama base URL, e.g. http://127.0.0.1:11434|Lokale Ollama-Basisadresse eingeben, z. B. http://127.0.0.1:11434
文件超过 512 MB 上限。请拆分后导入。|File exceeds 512 MB. Split it before importing.|Datei überschreitet 512 MB. Vor dem Import aufteilen.
PDF 已加密，请先解密。|PDF is encrypted. Decrypt it first.|PDF ist verschlüsselt. Zuerst entschlüsseln.
未提取到足够文本。扫描 PDF 请先 OCR 后导入。|Not enough text extracted. Run OCR on scanned PDFs before importing.|Nicht genügend Text erkannt. Bei gescannten PDFs vor dem Import OCR durchführen.
支持 .docx 和含文本的 .pdf；旧版 .doc 请另存为 .docx。|Use .docx or text .pdf; convert legacy .doc files to .docx.|.docx oder Text-.pdf verwenden; alte .doc-Dateien als .docx speichern.
请输入作者姓名。|Enter an author name.|Autorennamen eingeben.
{author} · {institution} · {identifier} · {count} 篇|{author} · {institution} · {identifier} · {count} papers|{author} · {institution} · {identifier} · {count} Arbeiten
模型下载未完成，请重试以继续下载。|Model download did not finish. Retry to resume.|Modelldownload unvollständig. Zum Fortsetzen erneut versuchen.
提取文本超过 1200 万字符。请拆分文档。|Extracted text exceeds 12 million characters. Split the document.|Extrahierter Text überschreitet 12 Millionen Zeichen. Dokument aufteilen.
Word 解压后超过 1 GB，请拆分文档。|Expanded Word file exceeds 1 GB. Split the document.|Entpackte Word-Datei überschreitet 1 GB. Dokument aufteilen.
论文下载地址无效。|Invalid paper download URL.|Ungültige Downloadadresse der Arbeit.
拒绝下载非公网地址。|Non-public download addresses are not allowed.|Nichtöffentliche Downloadadressen sind nicht erlaubt.
下载重定向次数过多。|Too many download redirects.|Zu viele Downloadweiterleitungen.
无效 OpenAlex 作者 ID。|Invalid OpenAlex author ID.|Ungültige OpenAlex-Autoren-ID.
导入已取消；已导入论文保留。|Import cancelled; previously imported papers are retained.|Import abgebrochen; bereits importierte Arbeiten bleiben erhalten.
OpenAlex 请求失败 ({status})。请检查网络、API key 或额度。|OpenAlex request failed ({status}). Check network, API key or quota.|OpenAlex-Anfrage fehlgeschlagen ({status}). Netzwerk, API-Schlüssel oder Kontingent prüfen.
检索已取消|Search cancelled|Suche abgebrochen
{title}：未找到公开 PDF，可手动导入。|{title}: No public PDF found; import manually.|{title}: Kein öffentliches PDF gefunden; manuell importieren.
{title}：{error}（下载或解析失败，可手动导入）|{title}: {error} (download / parsing failed; import manually)|{title}: {error} (Download / Verarbeitung fehlgeschlagen; manuell importieren)
论文 PDF 超过 512 MB。|Paper PDF exceeds 512 MB.|PDF der Arbeit überschreitet 512 MB.
链接返回网页而非 PDF，请手动下载全文后导入。|The link returned a webpage, not a PDF. Download the full text manually and import it.|Link lieferte eine Webseite statt eines PDFs. Volltext manuell herunterladen und importieren.
模型输出失败或被截断：{error}|Model output failed or was truncated: {error}|Modellausgabe fehlgeschlagen oder abgeschnitten: {error}
不支持此风格档案版本。|Unsupported style profile version.|Nicht unterstützte Stilprofilversion.
训练论文已被移除，请刷新文献库。|Training paper was removed. Refresh the library.|Trainingsarbeit wurde entfernt. Bibliothek aktualisieren.
风格规则格式错误，原模型保留。|Invalid style rule format; the previous profile is retained.|Ungültiges Stilregelformat; das bisherige Profil bleibt erhalten.

无法验证新安装的 Ollama 版本，请手动检查安装。|Cannot verify the installed Ollama version. Check the installation manually.|Installierte Ollama-Version konnte nicht geprüft werden. Installation manuell prüfen.
旧版 Ollama 仍在运行。请退出 Ollama 后重试。|The old Ollama server is still running. Quit Ollama and retry.|Der alte Ollama-Server läuft noch. Ollama beenden und erneut versuchen.
训练方式|Training method|Trainingsmethode
快速（推荐）：每篇最多 1 次 LLM|Fast (recommended): up to 1 LLM call per paper|Schnell (empfohlen): bis zu 1 LLM-Aufruf pro Arbeit
深入：每篇最多 3 次 LLM|Detailed: up to 3 LLM calls per paper|Vertieft: bis zu 3 LLM-Aufrufe pro Arbeit
全文保留用于检索；LLM 只学习代表性正文片段。成功片段自动缓存，重试或更新可复用。取消勾选 LLM 可快速建立纯统计档案。|Full text stays searchable; the LLM learns from representative excerpts. Completed samples are cached for retries and updates. Uncheck LLM for a fast statistics-only profile.|Volltexte bleiben durchsuchbar; das LLM lernt aus repräsentativen Auszügen. Erfolgreiche Analysen werden für Wiederholungen und Updates gespeichert. Ohne LLM wird schnell ein Statistikprofil erstellt.
全文索引 {current}/{total} · {title}|Full-text indexing {current}/{total} · {title}|Volltextindex {current}/{total} · {title}
风格学习 {current}/{total} · {title}|Style learning {current}/{total} · {title}|Stilanalyse {current}/{total} · {title}
缓存复用 {current}/{total} · {title}|Reusing cache {current}/{total} · {title}|Cache verwenden {current}/{total} · {title}
已用时 {minutes} 分 {seconds} 秒|Elapsed: {minutes} min {seconds} s|Dauer: {minutes} Min. {seconds} Sek.
训练统计：新调用 {calls} 次 · 缓存复用 {hits} 次 · 用时 {seconds} 秒|Training: {calls} new calls · {hits} cached samples · {seconds} seconds|Training: {calls} neue Aufrufe · {hits} Cache-Treffer · {seconds} Sekunden
风格学习请求超时，请使用更小的本地模型后重试。|Style learning timed out. Retry with a smaller local model.|Zeitlimit der Stilanalyse erreicht. Mit einem kleineren lokalen Modell erneut versuchen.

'''

CATALOG = {}
for line in _DATA.strip().splitlines():
    if not line.strip():
        continue
    source, english, german = line.split('|')
    CATALOG[source.replace('\\n', '\n')] = {'en': english.replace('\\n', '\n'), 'de': german.replace('\\n', '\n')}

_INSTALLER = {'Downloading the official Ollama Windows installer…': ('正在下载官方 Ollama Windows 安装程序…', 'Offizieller Ollama-Installer für Windows wird geladen…'), 'Downloading the official Ollama installer…': ('正在下载官方 Ollama 安装程序…', 'Offizieller Ollama-Installer wird geladen…'), 'Verifying the official installer signature…': ('正在验证官方安装程序签名…', 'Signatur des offiziellen Installers wird geprüft…'), 'Installing Ollama. Windows may request installation permission…': ('正在安装 Ollama，Windows 可能显示安装权限提示…', 'Ollama wird installiert. Windows kann eine Installationsberechtigung anfordern…'), 'Updating Ollama…': ('正在更新 Ollama…', 'Ollama wird aktualisiert…'), 'Installing Ollama…': ('正在安装 Ollama…', 'Ollama wird installiert…'), 'Windows Package Manager could not complete setup; using the official installer…': ('Windows 包管理器未能完成安装，正在使用官方安装程序…', 'Windows-Paketmanager konnte die Installation nicht abschließen; offizieller Installer wird verwendet…'), 'Verifying the downloaded application signature…': ('正在验证下载的应用签名…', 'Signatur der heruntergeladenen Anwendung wird geprüft…'), 'Restarting local Ollama with the updated application…': ('正在使用更新后的应用重启本机 Ollama…', 'Lokales Ollama wird mit der aktualisierten Anwendung neu gestartet…'), 'Ollama installed in ~/Applications. Previous user installation retained as a backup.': ('Ollama 已安装到 ~/Applications。此前用户安装已保留备份。', 'Ollama unter ~/Applications installiert. Vorherige Benutzerinstallation bleibt als Sicherung erhalten.'), 'Downloading Ollama: {size}': ('正在下载 Ollama：{size}', 'Ollama wird geladen: {size}'), 'Ollama installer command timed out.': ('Ollama 安装命令超时。', 'Zeitüberschreitung bei der Ollama-Installation.'), 'Ollama installation/update failed: {error}': ('Ollama 安装 / 更新失败：{error}', 'Ollama-Installation / Update fehlgeschlagen: {error}'), 'pulling manifest': ('正在获取模型清单', 'Modellmanifest wird geladen'), 'pulling {digest}': ('正在下载 {digest}', 'Download: {digest}'), 'verifying sha256 digest': ('正在校验模型文件', 'Modelldateien werden geprüft'), 'writing manifest': ('正在写入模型清单', 'Modellmanifest wird geschrieben'), 'success': ('成功', 'Erfolgreich')}
for source, (chinese, german) in _INSTALLER.items():
    CATALOG[source] = {"zh": chinese, "en": source, "de": german}

_PATTERNS = []
for source, translations in CATALOG.items():
    if '{' not in source:
        continue
    pattern = ''
    for literal, field, spec, conversion in Formatter().parse(source):
        pattern += re.escape(literal)
        if field:
            pattern += '(?P<' + field + '>.*?)'
    _PATTERNS.append((re.compile('^' + pattern + '$', re.DOTALL), translations))


def translate(text, language='zh'):
    """Translate app-owned messages. Captured names, manuscript excerpts and paths stay intact."""
    if text in CATALOG:
        return CATALOG[text].get(language, text)
    for pattern, translations in _PATTERNS:
        match = pattern.fullmatch(text)
        if match and language in translations:
            return translations[language].format(**match.groupdict())
    if '\n' in text:
        return '\n'.join(translate(line, language) for line in text.split('\n'))
    # Exception classes are diagnostic prefixes; translate only their message.
    prefix, separator, tail = text.partition(': ')
    if separator and prefix.endswith(('Error', 'Cancelled')):
        return prefix + separator + translate(tail, language)
    return text

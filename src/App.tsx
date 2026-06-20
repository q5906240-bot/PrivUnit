import {
  AlertTriangle,
  Check,
  Download,
  Eye,
  FilePlus2,
  Loader2,
  MousePointer2,
  Plus,
  Square,
  Trash2,
  Undo2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { convertFileSrc, isTauri } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";
import { stat } from "@tauri-apps/plugin-fs";
import { DEFAULT_EXPORT_COLOR, REDACTION_COLORS } from "./constants";
import { CATEGORY_LABELS_I18N, UI_TEXT, type Locale } from "./i18n";
import { analyzeWithSidecar, exportWithSidecar } from "./services/sidecar";
import type { Candidate, LoadedFile, MaterialType, RectNormalized } from "./types";
import { getExtension, makeFileId, validateFileLike } from "./utils/files";
import { pageAspectRatio } from "./utils/pageLayout";

const QUICK_CATEGORIES = [
  "person_name",
  "identity_number",
  "employer_name",
  "employer_logo",
  "employer_address",
  "department_name",
  "phone_number",
  "portrait",
  "seal",
] as const;

interface RemovedCandidate {
  fileId: string;
  candidate: Candidate;
  index: number;
}

export default function App() {
  const [locale, setLocale] = useState<Locale>("zh-CN");
  const [materialType, setMaterialType] = useState<MaterialType>("social");
  const [personName, setPersonName] = useState("");
  const [employerTermsText, setEmployerTermsText] = useState("");
  const [files, setFiles] = useState<LoadedFile[]>([]);
  const [activeFileId, setActiveFileId] = useState<string | null>(null);
  const [activePageIndex, setActivePageIndex] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState<(typeof QUICK_CATEGORIES)[number]>("person_name");
  const [selectedColor, setSelectedColor] = useState<string>(DEFAULT_EXPORT_COLOR);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [undoStack, setUndoStack] = useState<RemovedCandidate[]>([]);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [draftRect, setDraftRect] = useState<RectNormalized | null>(null);
  const previewRef = useRef<HTMLDivElement | null>(null);
  const t = UI_TEXT[locale];
  const categoryLabels = CATEGORY_LABELS_I18N[locale];

  useEffect(() => {
    document.title = t.appName;
  }, [t.appName]);

  const activeFile = files.find((file) => file.id === activeFileId) ?? files[0];
  const activePage = activeFile?.analysis?.pages.find((page) => page.index === activePageIndex) ?? activeFile?.analysis?.pages[0];
  const activeCandidates = useMemo(
    () =>
      activeFile?.analysis?.candidates.filter((candidate) => candidate.pageIndex === (activePage?.index ?? 0)) ?? [],
    [activeFile, activePage],
  );
  const approvedCount = files.reduce(
    (sum, file) => sum + (file.analysis?.candidates.filter((candidate) => candidate.status === "approved").length ?? 0),
    0,
  );
  const pendingCount = files.reduce(
    (sum, file) => sum + (file.analysis?.candidates.filter((candidate) => candidate.status === "pending").length ?? 0),
    0,
  );

  async function chooseFiles() {
    try {
      setMessage(null);
      const selected = await open({
        multiple: true,
        filters: [{ name: t.fileFilterName, extensions: ["pdf", "jpg", "jpeg", "png", "ipg"] }],
      });
      const paths = Array.isArray(selected) ? selected : selected ? [selected] : [];
      if (materialType === "social" && paths.length === 0 && files.length === 0) {
        setMessage(t.socialRequiresFile);
        return;
      }

      const loaded: LoadedFile[] = [];
      for (const path of paths) {
        const info = await stat(path);
        const name = path.split(/[\\/]/).pop() ?? path;
        const error = validateFileLike(name, Number(info.size), locale);
        if (error) {
          setMessage(`${name}: ${error}`);
          continue;
        }
        loaded.push({
          id: makeFileId(path, files.length + loaded.length),
          path,
          name,
          extension: getExtension(name),
          size: Number(info.size),
        });
      }
      setFiles((current) => [...current, ...loaded]);
      if (!activeFileId && loaded[0]) {
        setActiveFileId(loaded[0].id);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t.chooseFileFailed);
    }
  }

  async function analyzeFiles() {
    if (materialType === "social" && files.length === 0) {
      setMessage(t.socialRequiresFile);
      return;
    }
    setIsAnalyzing(true);
    setMessage(null);
    const employerTerms = employerTermsText
      .split(/[,，\n]/)
      .map((term) => term.trim())
      .filter(Boolean);

    try {
      const nextFiles: LoadedFile[] = [];
      for (const file of files) {
        const analysis = await analyzeWithSidecar({
          path: file.path,
          fileId: file.id,
          materialType,
          personName,
          employerTerms,
          locale,
        });
        nextFiles.push({ ...file, analysis });
      }
      setFiles(nextFiles);
      setUndoStack([]);
      setActiveFileId(nextFiles[0]?.id ?? null);
      setActivePageIndex(0);
      setMessage(t.analysisReady);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t.analysisFailed);
    } finally {
      setIsAnalyzing(false);
    }
  }

  function updateCandidate(candidate: Candidate, patch: Partial<Candidate>) {
    setFiles((current) =>
      current.map((file) => {
        if (file.id !== candidate.fileId || !file.analysis) return file;
        return {
          ...file,
          analysis: {
            ...file.analysis,
            candidates: file.analysis.candidates.map((item) =>
              item === candidate ||
              (item.fileId === candidate.fileId &&
                item.pageIndex === candidate.pageIndex &&
                item.category === candidate.category &&
                item.rectNormalized.x === candidate.rectNormalized.x &&
                item.rectNormalized.y === candidate.rectNormalized.y)
                ? { ...item, ...patch }
                : item,
            ),
          },
        };
      }),
    );
  }

  function removeFile(fileId: string) {
    setFiles((current) => current.filter((file) => file.id !== fileId));
    setUndoStack((current) => current.filter((item) => item.fileId !== fileId));
    if (activeFileId === fileId) {
      setActiveFileId(null);
      setActivePageIndex(0);
    }
  }

  function deleteCandidate(candidate: Candidate) {
    const sourceFile = files.find((file) => file.id === candidate.fileId);
    const candidates = sourceFile?.analysis?.candidates ?? [];
    const index = candidates.findIndex((item) => isSameCandidate(item, candidate));
    if (!sourceFile?.analysis || index < 0) return;

    const removed: RemovedCandidate = {
      fileId: sourceFile.id,
      candidate: candidates[index],
      index,
    };

    setFiles((current) =>
      current.map((file) => {
        if (file.id !== removed.fileId || !file.analysis) return file;
        return {
          ...file,
          analysis: {
            ...file.analysis,
            candidates: file.analysis.candidates.filter((item) => !isSameCandidate(item, removed.candidate)),
          },
        };
      }),
    );
    setUndoStack((current) => [...current, removed].slice(-20));
    setMessage(t.candidateDeleted);
  }

  function undoDeleteCandidate() {
    const removed = undoStack[undoStack.length - 1];
    if (!removed) return;

    setFiles((current) =>
      current.map((file) => {
        if (file.id !== removed.fileId || !file.analysis) return file;
        if (file.analysis.candidates.some((candidate) => isSameCandidate(candidate, removed.candidate))) return file;
        const candidates = [...file.analysis.candidates];
        const index = Math.min(Math.max(removed.index, 0), candidates.length);
        candidates.splice(index, 0, removed.candidate);
        return {
          ...file,
          analysis: {
            ...file.analysis,
            candidates,
          },
        };
      }),
    );
    setUndoStack((current) => current.slice(0, -1));
    setActiveFileId(removed.fileId);
    setActivePageIndex(removed.candidate.pageIndex);
    setMessage(t.deleteUndone);
  }

  async function exportActiveFile() {
    if (!activeFile?.analysis) {
      setMessage(t.analyzeFirst);
      return;
    }
    const candidates = activeFile.analysis.candidates.filter((candidate) => candidate.status === "approved");
    if (candidates.length === 0) {
      setMessage(t.approveOne);
      return;
    }
    setIsExporting(true);
    setMessage(null);
    try {
      const target = await save({
        defaultPath: activeFile.name.replace(
          /(\.[^.]+)?$/,
          `${t.redactedSuffix}.${activeFile.extension === "jpg" ? "png" : activeFile.extension}`,
        ),
        filters: [{ name: t.exportFilterName, extensions: [activeFile.extension === "jpg" ? "png" : activeFile.extension] }],
      });
      if (!target) return;
      const outputPath = await exportWithSidecar({
        sourcePath: activeFile.path,
        outputPath: target,
        candidates,
        locale,
      });
      setMessage(`${t.exported}${outputPath}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t.exportFailed);
    } finally {
      setIsExporting(false);
    }
  }

  function pointFromEvent(event: React.PointerEvent<HTMLDivElement>) {
    const bounds = previewRef.current?.getBoundingClientRect();
    if (!bounds) return null;
    return {
      x: clamp((event.clientX - bounds.left) / bounds.width),
      y: clamp((event.clientY - bounds.top) / bounds.height),
    };
  }

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (!activeFile?.analysis) return;
    const point = pointFromEvent(event);
    if (!point) return;
    setDragStart(point);
    setDraftRect({ x: point.x, y: point.y, width: 0, height: 0 });
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragStart) return;
    const point = pointFromEvent(event);
    if (!point) return;
    setDraftRect(rectFromPoints(dragStart, point));
  }

  function handlePointerUp() {
    if (!activeFile?.analysis || !draftRect || draftRect.width < 0.01 || draftRect.height < 0.01) {
      setDragStart(null);
      setDraftRect(null);
      return;
    }

    const manual: Candidate = {
      fileId: activeFile.id,
      pageIndex: activePage?.index ?? 0,
      rectNormalized: draftRect,
      category: selectedCategory,
      source: "manual",
      confidence: 1,
      status: "approved",
      color: selectedColor,
      text: null,
    };
    setFiles((current) =>
      current.map((file) =>
        file.id === activeFile.id && file.analysis
          ? { ...file, analysis: { ...file.analysis, candidates: [...file.analysis.candidates, manual] } }
          : file,
      ),
    );
    setDragStart(null);
    setDraftRect(null);
  }

  return (
    <main className="shell">
      <section className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Eye size={20} />
          </div>
          <div>
            <h1>{t.appName}</h1>
            <p>{t.appSubtitle}</p>
          </div>
        </div>

        <div className="panel">
          <label className="field-label">{t.materialType}</label>
          <div className="segmented">
            <button className={materialType === "social" ? "active" : ""} onClick={() => setMaterialType("social")}>
              {t.socialType}
            </button>
            <button className={materialType === "other" ? "active" : ""} onClick={() => setMaterialType("other")}>
              {t.otherType}
            </button>
          </div>
          <label className="field-label" htmlFor="personName">
            {t.personName}
          </label>
          <input id="personName" value={personName} onChange={(event) => setPersonName(event.target.value)} placeholder={t.personNamePlaceholder} />
          <label className="field-label" htmlFor="employerTerms">
            {t.employerTerms}
          </label>
          <textarea
            id="employerTerms"
            value={employerTermsText}
            onChange={(event) => setEmployerTermsText(event.target.value)}
            placeholder={t.employerTermsPlaceholder}
          />
          <div className="action-row">
            <button className="primary" onClick={chooseFiles}>
              <FilePlus2 size={16} />
              {t.addFile}
            </button>
            <button className="secondary" onClick={analyzeFiles} disabled={isAnalyzing || files.length === 0}>
              {isAnalyzing ? <Loader2 className="spin" size={16} /> : <MousePointer2 size={16} />}
              {isAnalyzing ? t.analyzing : t.generateCandidates}
            </button>
          </div>
        </div>

        <div className="panel file-list">
          <div className="panel-title">{t.files}</div>
          {files.length === 0 ? (
            <div className="empty">{t.emptyFileHint}</div>
          ) : (
            files.map((file) => (
              <button
                className={`file-item ${activeFile?.id === file.id ? "active" : ""}`}
                key={file.id}
                onClick={() => {
                  setActiveFileId(file.id);
                  setActivePageIndex(0);
                }}
              >
                <span>
                  <strong>{file.name}</strong>
                  <small>{formatBytes(file.size)}</small>
                </span>
                <Trash2
                  size={15}
                  onClick={(event) => {
                    event.stopPropagation();
                    removeFile(file.id);
                  }}
                />
              </button>
            ))
          )}
        </div>

        <div className="stats">
          <span>{pendingCount} {t.pending}</span>
          <span>{approvedCount} {t.approved}</span>
        </div>
      </section>

      <section className="workspace">
        <header className="toolbar">
          <div className="tool-group">
            <label>{t.manualBox}</label>
            <select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value as typeof selectedCategory)}>
              {QUICK_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {categoryLabels[category]}
                </option>
              ))}
            </select>
            <div className="swatches">
              {REDACTION_COLORS.map((color) => (
                <button
                  key={color}
                  aria-label={`${t.selectColor} ${color}`}
                  className={selectedColor === color ? "selected" : ""}
                  style={{ backgroundColor: color }}
                  onClick={() => setSelectedColor(color)}
                />
              ))}
            </div>
          </div>
          <div className="tool-group">
            <div className="language-switch" aria-label="Language">
              <button className={locale === "zh-CN" ? "active" : ""} onClick={() => setLocale("zh-CN")}>
                {t.zhShort}
              </button>
              <button className={locale === "en" ? "active" : ""} onClick={() => setLocale("en")}>
                EN
              </button>
            </div>
            {activeFile?.analysis?.pages.map((page) => (
              <button
                key={page.index}
                className={activePageIndex === page.index ? "page active" : "page"}
                onClick={() => setActivePageIndex(page.index)}
              >
                {page.index + 1}
              </button>
            ))}
            <button className="primary" onClick={exportActiveFile} disabled={isExporting || !activeFile?.analysis}>
              <Download size={16} />
              {isExporting ? t.exporting : t.exportCurrentFile}
            </button>
          </div>
        </header>

        {message && (
          <div className="notice">
            <AlertTriangle size={16} />
            {message}
          </div>
        )}

        <div className="work-grid">
          <div className="preview-shell">
            <div
              className="document-preview"
              style={{ aspectRatio: pageAspectRatio(activePage) }}
              ref={previewRef}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
            >
              {activePage?.imagePath ? (
                <img src={toAssetUrl(activePage.imagePath)} alt={t.materialPreviewAlt} draggable={false} />
              ) : (
                <div className="preview-placeholder">
                  <Square size={32} />
                  <span>{activeFile ? t.previewAfterAnalysis : t.addMaterialFile}</span>
                </div>
              )}
              {activeCandidates.map((candidate, index) => (
                <button
                  key={`${candidate.category}-${candidate.pageIndex}-${index}`}
                  className={`redaction-box ${candidate.status}`}
                  style={boxStyle(candidate)}
                  title={`${categoryLabels[candidate.category]} ${Math.round(candidate.confidence * 100)}%`}
                  onClick={(event) => {
                    event.stopPropagation();
                    updateCandidate(candidate, {
                      status: candidate.status === "approved" ? "pending" : "approved",
                    });
                  }}
                />
              ))}
              {draftRect && <div className="redaction-box draft" style={rectStyle(draftRect, selectedColor)} />}
              {isAnalyzing && (
                <div className="analysis-overlay" aria-live="polite">
                  <div className="analysis-card">
                    <Loader2 className="spin" size={24} />
                    <strong>{t.analyzingMaterial}</strong>
                    <span>{t.analyzingDetail}</span>
                    <div className="analysis-progress" />
                  </div>
                </div>
              )}
            </div>
          </div>

          <aside className="candidate-panel">
            <div className="panel-title candidate-panel-title">
              <span>{t.candidates}</span>
              <button className="undo-action" onClick={undoDeleteCandidate} disabled={undoStack.length === 0} title={t.undoDelete}>
                <Undo2 size={14} />
                {t.undo}
              </button>
            </div>
            {isAnalyzing ? (
              <div className="candidate-skeletons" aria-hidden="true">
                {[0, 1, 2].map((item) => (
                  <div className="candidate-skeleton" key={item}>
                    <span />
                    <small />
                  </div>
                ))}
              </div>
            ) : activeCandidates.length === 0 ? (
              <div className="empty">{t.emptyCandidates}</div>
            ) : (
              activeCandidates.map((candidate, index) => (
                <div className="candidate" key={`${candidate.category}-${index}`}>
                  <div>
                    <strong>{categoryLabels[candidate.category]}</strong>
                    <small>
                      {candidate.source} · {Math.round(candidate.confidence * 100)}%
                    </small>
                    {candidate.text && <p>{candidate.text}</p>}
                  </div>
                  <div className="candidate-actions">
                    <button
                      className={candidate.status === "approved" ? "ok active" : "ok"}
                      onClick={() => updateCandidate(candidate, { status: "approved" })}
                      title={t.confirmRedaction}
                    >
                      <Check size={15} />
                    </button>
                    <button
                      className="danger"
                      onClick={() => deleteCandidate(candidate)}
                      title={t.deleteCandidate}
                    >
                      <X size={15} />
                    </button>
                  </div>
                </div>
              ))
            )}
            <button
              className="secondary full"
              onClick={() => {
                if (!activeFile?.analysis) return;
                const manual: Candidate = {
                  fileId: activeFile.id,
                  pageIndex: activePage?.index ?? 0,
                  rectNormalized: { x: 0.2, y: 0.2, width: 0.25, height: 0.08 },
                  category: selectedCategory,
                  source: "manual",
                  confidence: 1,
                  status: "approved",
                  color: selectedColor,
                  text: null,
                };
                setFiles((current) =>
                  current.map((file) =>
                    file.id === activeFile.id && file.analysis
                      ? { ...file, analysis: { ...file.analysis, candidates: [...file.analysis.candidates, manual] } }
                      : file,
                  ),
                );
              }}
            >
              <Plus size={16} />
              {t.addDefaultBox}
            </button>
          </aside>
        </div>
      </section>
    </main>
  );
}

function clamp(value: number) {
  return Math.min(1, Math.max(0, value));
}

function rectFromPoints(start: { x: number; y: number }, end: { x: number; y: number }): RectNormalized {
  const x = Math.min(start.x, end.x);
  const y = Math.min(start.y, end.y);
  return {
    x,
    y,
    width: Math.abs(start.x - end.x),
    height: Math.abs(start.y - end.y),
  };
}

function rectStyle(rect: RectNormalized, color: string): React.CSSProperties {
  return {
    left: `${rect.x * 100}%`,
    top: `${rect.y * 100}%`,
    width: `${rect.width * 100}%`,
    height: `${rect.height * 100}%`,
    backgroundColor: color,
  };
}

function boxStyle(candidate: Candidate): React.CSSProperties {
  return {
    ...rectStyle(candidate.rectNormalized, candidate.color),
    opacity: candidate.status === "rejected" ? 0.16 : candidate.status === "approved" ? 0.72 : 0.38,
  };
}

function isSameCandidate(left: Candidate, right: Candidate) {
  return (
    left.fileId === right.fileId &&
    left.pageIndex === right.pageIndex &&
    left.category === right.category &&
    left.source === right.source &&
    left.rectNormalized.x === right.rectNormalized.x &&
    left.rectNormalized.y === right.rectNormalized.y &&
    left.rectNormalized.width === right.rectNormalized.width &&
    left.rectNormalized.height === right.rectNormalized.height
  );
}

function formatBytes(size: number) {
  return `${(size / 1024 / 1024).toFixed(2)} MiB`;
}

function toAssetUrl(path: string) {
  if (isTauri()) {
    return convertFileSrc(path);
  }
  return "";
}

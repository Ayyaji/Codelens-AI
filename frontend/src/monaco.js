import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";

self.MonacoEnvironment = {
  getWorker() {
    return new editorWorker();
  },
};

loader.config({ monaco });

monaco.editor.defineTheme("codelens", {
  base: "vs-dark",
  inherit: true,
  rules: [],
  colors: {
    "editor.background": "#0c1016",
    "editor.foreground": "#e8eaee",
    "editorLineNumber.foreground": "#5d6676",
    "editorLineNumber.activeForeground": "#8d96a6",
    "editor.selectionBackground": "#243044",
    "editorCursor.foreground": "#4d9de0",
    "editorWidget.background": "#131922",
    "editorWidget.border": "#242c38",
  },
});

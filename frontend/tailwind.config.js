/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0c1016",
        panel: "#131922",
        line: "#242c38",
        paper: "#e8eaee",
        mute: "#8d96a6",
        faint: "#5d6676",
        full: "#e8a33d",
        hint: "#4d9de0",
        gentle: "#8b7fd1",
        break: "#e15b6a",
        ok: "#3cbe8c",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        inset: "inset 0 0 0 1px #242c38",
      },
    },
  },
  plugins: [],
};

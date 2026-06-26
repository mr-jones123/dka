import { useMemo, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight, CheckCircle2, Copy, FileText, Menu, Terminal, X } from "lucide-react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const commands = [
  {
    name: "Initialize",
    command: "uv run dka init path/to/dataset",
    result: [
      "Created dka dataset at /path/to/dataset",
      "raw/audio/ ready",
      "raw/metadata.csv scaffolded",
      "dka.yaml written with default speech settings",
    ],
  },
  {
    name: "Validate",
    command: "uv run dka validate examples/bisaya-commons",
    result: [
      "Validation",
      "Rows: 3",
      "Blocking issues: 0",
      "Supported audio and transcript columns confirmed",
    ],
  },
  {
    name: "Build",
    command: "uv run dka build examples/bisaya-web",
    result: [
      "dka build complete",
      "Samples: 14",
      "Hours: 0.0357",
      "Flagged samples: 0",
    ],
  },
  {
    name: "Export",
    command:
      "uv run dka build data/pld-ceb/PLD/CEB --preset pld --out datasets/pld-ceb-5k --limit 5000 --hf",
    result: [
      "Imported 5000 PLD rows.",
      "Samples: 5000",
      "Hours: 6.5072",
      "Exported hf dataset to datasets/pld-ceb-5k/exports/hf",
    ],
  },
  {
    name: "Train",
    command: "uv run python scripts/train_whisper.py datasets/pld-ceb-5k --steps 500",
    result: [
      "train loss: 19.95 -> 2.15",
      "eval loss: 1.08 -> 0.62",
      "best CER: 23.25%",
      "best WER: 64.93%",
    ],
  },
];

const cards = [
  {
    number: "01",
    title: "Raw speech in",
    text: "Start with audio, transcript rows, language metadata, and a dka.yaml contract.",
  },
  {
    number: "02",
    title: "Clean artifacts out",
    text: "Write mono 16kHz WAV files, normalized metadata, splits, and quality reports.",
    accent: true,
  },
  {
    number: "03",
    title: "Training path ready",
    text: "Export Hugging Face CSVs and feed the included Whisper fine-tuning scripts.",
  },
];

function App() {
  const root = useRef<HTMLElement | null>(null);
  const [activeCommand, setActiveCommand] = useState(2);
  const [copied, setCopied] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const currentCommand = commands[activeCommand];
  const terminalRows = useMemo(
    () => currentCommand.result.map((row, index) => `${activeCommand}-${index}-${row}`),
    [activeCommand, currentCommand.result],
  );

  useGSAP(
    () => {
      gsap.fromTo(
        ".hero-title span",
        { yPercent: 18, opacity: 0 },
        { yPercent: 0, opacity: 1, duration: 0.9, ease: "power3.out", stagger: 0.12 },
      );

      gsap.utils.toArray<HTMLElement>(".reveal-plate").forEach((element) => {
        gsap.fromTo(
          element,
          { y: 54, opacity: 0, scale: 0.96 },
          {
            y: 0,
            opacity: 1,
            scale: 1,
            ease: "power2.out",
            scrollTrigger: {
              trigger: element,
              start: "top 84%",
              end: "top 48%",
              scrub: true,
            },
          },
        );
      });

      gsap.fromTo(
        ".terminal-plate",
        { y: 64, opacity: 0.6 },
        {
          y: 0,
          opacity: 1,
          ease: "none",
          scrollTrigger: {
            trigger: ".simulator-section",
            start: "top 78%",
            end: "bottom 48%",
            scrub: true,
          },
        },
      );
    },
    { scope: root },
  );

  async function copyInstallCommand() {
    await navigator.clipboard.writeText("pip install dka-speech");
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <main ref={root} className="site-shell">
      <section id="top" className="opencode-frame">
        <nav className="top-strip" aria-label="Primary navigation">
          <a href="#top" className="brand" aria-label="DKA home">
            dka
          </a>
          <button
            className="menu-toggle"
            type="button"
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={24} strokeWidth={2.4} /> : <Menu size={24} strokeWidth={2.4} />}
          </button>
          <div className={menuOpen ? "nav-menu open" : "nav-menu"}>
            <a href="#simulator" onClick={() => setMenuOpen(false)}>
              Simulator
            </a>
            <a href="#stats" onClick={() => setMenuOpen(false)}>
              Model stats
            </a>
            <a href="#install" onClick={() => setMenuOpen(false)}>
              Install
            </a>
          </div>
        </nav>

        <div className="hero-section">
          <p className="kicker">Low-resource language tooling for Bisaya and beyond</p>
          <h1 className="hero-title" aria-label="For Filipinos. By a Filipino.">
            <span>For Filipinos.</span>
            <span className="hero-ox">By a Filipino.</span>
          </h1>
          <p className="hero-copy">
            dka is a Python CLI for preparing underrepresented Philippine speech datasets.
            It turns regional recordings and transcripts into clean WAV clips, documented
            splits, quality reports, dataset cards, and exports for Whisper-style ASR training.
          </p>
          <div className="install-command" role="group" aria-label="Install command">
            <code>pip install dka-speech</code>
            <button type="button" onClick={copyInstallCommand} aria-label="Copy pip install command">
              <Copy size={17} strokeWidth={2.4} />
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      </section>

      <section className="card-strip" aria-label="DKA artifact path">
        <div className="strip-heading">
          <h2>
            What does <span>dka</span> prepare?
          </h2>
          <p>[ 03 outputs / speech data ]</p>
        </div>
        <div className="cards-grid">
          {cards.map((card) => (
            <article
              key={card.title}
              className={card.accent ? "sign-plate sign-plate-gold reveal-plate" : "sign-plate reveal-plate"}
            >
              <div className="card-topline">
                <span>Artifact / {card.number}</span>
                <span aria-hidden>{"///"}</span>
              </div>
              <h3>{card.title}</h3>
              <p>{card.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="simulator" className="simulator-section">
        <div className="simulator-heading reveal-plate">
          <p className="kicker">Interactive CLI simulator</p>
          <h2>Keep the command-line moment. Make it feel like a signboard.</h2>
        </div>
        <div className="simulator-grid">
          <div className="command-list" role="tablist" aria-label="DKA command stages">
            {commands.map((item, index) => (
              <button
                key={item.name}
                className={index === activeCommand ? "command-button active" : "command-button"}
                onClick={() => setActiveCommand(index)}
                role="tab"
                aria-selected={index === activeCommand}
              >
                <span>{item.name}</span>
                <ArrowRight size={17} strokeWidth={2.3} />
              </button>
            ))}
          </div>

          <article className="terminal-plate reveal-plate">
            <div className="terminal-top">
              <Terminal size={19} strokeWidth={2.2} />
              <span>dka shell</span>
            </div>
            <pre>
              <code>$ {currentCommand.command}</code>
            </pre>
            <div className="terminal-output">
              {terminalRows.map((id, index) => (
                <p key={id}>{currentCommand.result[index]}</p>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section id="stats" className="evidence-section">
        <div className="evidence-card sign-plate reveal-plate">
          <FileText size={30} strokeWidth={2.3} />
          <h2>Real outputs from this repo.</h2>
          <div className="metrics-grid">
            <Metric label="pld-ceb-5k" value="5,000 samples" detail="6.5072 hours · 14 speakers" />
            <Metric label="pld-hil-5k" value="5,000 samples" detail="6.1419 hours · 13 speakers" />
            <Metric label="bisaya-web" value="14 samples" detail="0.0357 hours · 0 flags" />
            <Metric label="Whisper prototype" value="loss 19.95 -> 2.15" detail="training loss improved over 500 steps" />
            <Metric label="Evaluation" value="loss 1.08 -> 0.62" detail="validation loss moved in the right direction" />
            <Metric label="Best CER" value="23.25%" detail="character error rate on the prototype run" />
          </div>
        </div>
      </section>

      <section id="install" className="bottom-placard">
        <span aria-hidden className="bolt bolt-a" />
        <span aria-hidden className="bolt bolt-b" />
        <span aria-hidden className="bolt bolt-c" />
        <span aria-hidden className="bolt bolt-d" />

        <p className="kicker">Install and verify</p>
        <h2>One small step for man. One giant leap for Filipino research.</h2>
        <div className="install-row">
          <div>
            <a
              href="https://github.com/mr-jones123/dka"
              className="btn-light"
              target="_blank"
              rel="noreferrer"
            >
              <CheckCircle2 size={20} strokeWidth={2.3} />
              View on GitHub
            </a>
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <span>dka showcase</span>
        <span>Made by Xynil Jhed Lacap</span>
      </footer>
    </main>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

export default App;

"""Rebuild narrated README GIFs from SVG keyframes with bounded external tools.

Requires rsvg-convert and ffmpeg. Frames/logs stay in .harness/reports;
rendering is sequential and ffmpeg uses one thread. No environments are installed.
The example outcomes were verified against the generated library's real checks.
"""

from dataclasses import dataclass
from html import escape
from pathlib import Path

from python_agent_harness.model import Check
from python_agent_harness.paths import HarnessError
from python_agent_harness.runner import execute

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".harness/reports/readme-media/render"
COLORS = {"$": "#8ee5c7", "+": "#8ee5c7", "!": "#ffabb0", "#": "#9aaec7"}


@dataclass(frozen=True, slots=True, kw_only=True)
class Scene:
    """A short narrated step, deliberately distinct from raw terminal output."""

    title: str
    note: str
    lines: tuple[str, ...]


SOLUTION = (
    Scene(
        title="Agree what the result should mean.",
        note="Your team's requirement becomes an explicit expectation.",
        lines=("# THE CONTRACT", "Net total = gross - flat fee", "100 - 7 = 93"),
    ),
    Scene(
        title="Give the expectation an independent test.",
        note="The expected value comes from the requirement.",
        lines=(
            "# tests/test_totals.py",
            "assert net_total(100, 7) == 93",
            "assert net_total(100, 0) == 100",
        ),
    ),
    Scene(
        title="Run the agreed checks before review.",
        note="The same configured checks run locally and in CI.",
        lines=("$ just check", "+ package     PASS", "+ static      PASS", "! tests       FAIL"),
    ),
    Scene(
        title="Send a concrete failure back to the author.",
        note="Actual failure from the isolated example.",
        lines=(
            "# test_flat_fee_is_deducted",
            "! E   assert 107 == 93",
            "! 1 failed, 2 passed",
            "The fee was added, not deducted.",
        ),
    ),
    Scene(
        title="Correct the source. Keep the expectation.",
        note="The test stays the same while the implementation is fixed.",
        lines=(
            "# src/my_project/totals.py",
            "! - return gross + fee",
            "+ + return gross - fee",
            "# assert net_total(100, 7) == 93",
        ),
    ),
    Scene(
        title="Accept current evidence from the checks.",
        note="Review still matters. Repeated mechanical feedback arrives earlier.",
        lines=(
            "$ just check",
            "+ package / static / tests     PASS",
            "+ 3 passed",
            "+ gate: current reports        PASS",
        ),
    ),
)

INSTALL = (
    Scene(
        title="Get the constructor.",
        note="Python 3.13+, Git, uv and just; Linux or macOS.",
        lines=(
            "$ git clone https://github.com/Selone-x/python-agent-harness",
            "$ cd python-agent-harness",
            "$ uv sync --locked --no-dev",
            "# Constructor runtime installed; no tool migration.",
        ),
    ),
    Scene(
        title="Create your first project.",
        note="Scaffold into an empty destination; choose a real package name.",
        lines=(
            "$ uv run --locked --no-dev harness --root ../my-project init \\",
            "    --name my-project --package my_project --kind library \\",
            "    --provider github --scaffold",
            "+ Draft specification and project files created.",
        ),
    ),
    Scene(
        title="Agree the requirements before generating CI.",
        note="Set purpose, source roots, boundaries and acceptance criteria.",
        lines=(
            "# Review .harness/project.toml with your agent.",
            "$ uv run --locked --no-dev harness \\",
            "    --root ../my-project validate",
            "+ Specification validated; review requirements visible.",
        ),
    ),
    Scene(
        title="Preview the workflow, then apply it.",
        note="Inspect the proposed changes before applying them.",
        lines=(
            "$ uv run --locked --no-dev harness \\",
            "    --root ../my-project render",
            "# Review the preview.",
            "$ uv run --locked --no-dev harness \\",
            "    --root ../my-project render --apply",
        ),
    ),
    Scene(
        title="Install the agreed project tools.",
        note="Setup creates uv.lock and installs the static pre-commit hook.",
        lines=(
            "$ cd ../my-project",
            "$ git init -b feat/bootstrap",
            "$ just setup",
            "+ Project toolchain and pre-commit ready.",
        ),
    ),
    Scene(
        title="See the scaffold's checks run.",
        note="The initial version test is a smoke test. Add your behavior tests.",
        lines=(
            "$ just check",
            "+ package / static / tests     PASS",
            "+ 1 passed (scaffold smoke test)",
            "+ gate: current reports        PASS",
        ),
    ),
)


def text(
    x: int, y: int, value: str, size: int = 18, color: str = "#e8effa", mono: bool = False
) -> str:
    """Escape all displayed command text before embedding it in SVG."""
    family = "DejaVu Sans Mono, monospace" if mono else "DejaVu Sans, sans-serif"
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" '
        f'font-size="{size}" fill="{color}">{escape(value)}</text>'
    )


def box(x: int, y: int, width: int, height: int, fill: str, stroke: str = "none") -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="12" fill="{fill}" stroke="{stroke}"/>'
    )


def shell(scene: Scene, index: int, mode: str) -> str:
    """A dark canvas carries the before/after story with error and success accents."""
    result = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="640" '
        'viewBox="0 0 1120 640" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(scene.title)}</title>',
        f'<desc id="description">{escape(scene.note)} '
        "Narrated replay of verified example results.</desc>",
        box(1, 1, 1118, 638, "#0d1420", "#28374b"),
        text(40, 42, "PYTHON AGENT HARNESS", 13, "#70ddba"),
        text(864, 42, f"{index + 1:02d} / 06   {mode.upper()}", 13, "#8398b4"),
        text(40, 91, scene.title, 29),
        text(40, 124, scene.note, 17, "#a6b8ce"),
    ]
    for number in range(6):
        result.append(
            box(40 + number * 174, 569, 160, 5, "#69d7b1" if number <= index else "#27374a")
        )
    result.append(
        text(40, 609, "ISOLATED EXAMPLE  /  ACTUAL OUTCOMES  /  SUMMARIZED PLAYBACK", 12, "#8398b4")
    )
    return "".join(result)


def terminal(
    x: int, y: int, width: int, scene: Scene, visible: int, size: int, height: int = 352
) -> str:
    result = [
        box(x, y, width, height, "#0b1728"),
        text(x + 22, y + 29, "harness  /  replay", 12, "#91a6c0"),
    ]
    for index, line in enumerate(scene.lines[:visible]):
        color = COLORS.get(line[:1], "#e1e9f5")
        content = line[2:] if line.startswith(("+ ", "! ")) else line
        result.append(text(x + 22, y + 78 + index * 45, content, size, color, mono=True))
    result.append(box(x + 22, y + height - 43, 8, 16, "#8ee5c7"))
    return "".join(result)


def solution(scene: Scene, index: int, visible: int) -> str:
    result = [
        shell(scene, index, "workflow"),
        box(40, 158, 398, 376, "#2a1e27", "#593b45"),
        text(61, 193, "BEFORE / REVIEW QUEUE", 13, "#ee9c94"),
        box(59, 215, 360, 120, "#0d1420"),
        text(77, 241, "totals.py", 13, "#b497a2"),
        text(77, 278, "def net_total(gross, fee):", 17, mono=True),
        text(77, 309, "  return gross + fee", 17, "#ff9a9b", mono=True),
        text(63, 384, "“The fee should be deducted.”", 18, "#e3b3b0"),
        text(63, 426, "“Please rerun the checks.”", 18, "#e3b3b0"),
        text(63, 502, "Repeated feedback in the PR.", 15, "#bb9299"),
        box(460, 158, 620, 376, "#142f2a", "#31584e"),
        text(481, 193, "AFTER / EXECUTABLE FEEDBACK", 13, "#83dfbc"),
        terminal(478, 210, 584, scene, visible, 17, height=305),
    ]
    return "".join(result) + "</svg>"


def installation(scene: Scene, index: int, visible: int) -> str:
    files = (
        ("python-agent-harness/", 0),
        ("  .venv/", 0),
        ("my-project/", 1),
        ("  src/my_project/", 1),
        ("  tests/", 1),
        ("  lint-rules/", 1),
        ("  .harness/project.toml", 1),
        ("  .harness/runner.pyz", 3),
        ("  .github/workflows/", 3),
        ("  AGENTS.md", 3),
        ("  uv.lock", 4),
    )
    result = [
        shell(scene, index, "install"),
        terminal(40, 158, 712, scene, visible, 14),
        box(772, 158, 308, 352, "#142f2a", "#31584e"),
        text(794, 192, "YOUR WORKSPACE", 13, "#83dfbc"),
    ]
    for number, (name, appears) in enumerate(files):
        if index >= appears:
            result.append(text(794, 229 + number * 24, name, 15, "#bce4d4", mono=True))
    return "".join(result) + "</svg>"


def run(name: str, arguments: tuple[str, ...]) -> None:
    result = execute(
        ROOT, Check(id=f"media-{name}", group="deep", argv=arguments, timeout=120), 65536
    )
    if result.status != "pass":
        raise HarnessError(
            f"Media command {name} failed; inspect .harness/reports/logs/media-{name}.log"
        )


def encode(name: str, manifest: Path, destination: Path) -> None:
    palette = manifest.with_name("palette.png")
    prefix = (
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-filter_complex_threads",
        "1",
    )
    inputs = ("-f", "concat", "-safe", "0", "-i", str(manifest))
    run(
        f"{name}-palette",
        (
            *prefix,
            *inputs,
            "-vf",
            "palettegen=max_colors=128",
            "-frames:v",
            "1",
            str(palette),
        ),
    )
    graph = "[0:v][1:v]paletteuse=dither=none:diff_mode=rectangle"
    run(
        f"{name}-gif",
        (
            *prefix,
            *inputs,
            "-i",
            str(palette),
            "-filter_complex",
            graph,
            "-fps_mode",
            "vfr",
            "-loop",
            "0",
            str(destination),
        ),
    )


def render(name: str, scenes: tuple[Scene, ...], poster: str) -> None:
    folder = WORK / name
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    painter = solution if name == "demo" else installation
    for index, scene in enumerate(scenes):
        for visible in range(1, len(scene.lines) + 1):
            number = len(frames)
            source = folder / f"{number:03d}.svg"
            target = source.with_suffix(".png")
            source.write_text(painter(scene, index, visible), encoding="utf-8")
            run(f"{name}-{number}", ("rsvg-convert", "--output", str(target), str(source)))
            duration = 2.0 if visible == len(scene.lines) else 0.35
            frames.append(f"file '{target.name}'\nduration {duration}\n")
    if not frames:
        raise HarnessError("At least one nonempty scene is required")
    last = folder / f"{len(frames) - 1:03d}.png"
    manifest = folder / "frames.ffconcat"
    manifest.write_text("".join(frames) + f"file '{last.name}'\n", encoding="utf-8")
    (ROOT / "assets" / poster).write_text(
        painter(scenes[-1], len(scenes) - 1, len(scenes[-1].lines)), encoding="utf-8"
    )
    destination = ROOT / "assets" / f"readme-{name}.gif"
    encode(name, manifest, destination)
    print(f"Rendered {destination.name}: {destination.stat().st_size:,} bytes", flush=True)


def main() -> None:
    render("demo", SOLUTION, "readme-hero.svg")
    render("install", INSTALL, "readme-install.svg")


if __name__ == "__main__":
    main()

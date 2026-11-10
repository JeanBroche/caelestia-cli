import json
import random
from pathlib import Path
from typing import Any

from caelestia.utils.notify import notify
from caelestia.utils.paths import atomic_dump, scheme_data_dir, scheme_path, user_schemes_dir


class Scheme:
    _name: str
    _flavour: str
    _mode: str
    _variant: str
    _colours: dict[str, str]
    _dir: Path
    notify: bool

    def __init__(self, scheme_json: dict[str, Any] | None) -> None:
        if scheme_json is None:
            self._name = "catppuccin"
            self._flavour = "mocha"
            self._mode = "dark"
            self._variant = "tonalspot"
            self._dir = scheme_data_dir
            self._colours = read_colours_from_file(self.get_colours_path())
        else:
            self._name = scheme_json["name"]
            self._flavour = scheme_json["flavour"]
            self._mode = scheme_json["mode"]
            self._variant = scheme_json["variant"]
            self._colours = scheme_json["colours"]
            self._dir = Path(scheme_json["dir"])
        self.notify = False

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if name == self._name:
            return

        integrated_schemes = get_scheme_names()
        user_schemes = get_custom_scheme_names()
        valid_schemes = integrated_schemes + user_schemes

        if name not in valid_schemes:
            if self.notify:
                notify(
                    "-u",
                    "critical",
                    "Unable to set scheme",
                    f'"{name}" is not a valid scheme.\nValid schemes are: {valid_schemes}',
                )
            raise ValueError(f"Invalid scheme name: {name}")

        if name in user_schemes:
            self._dir= user_schemes_dir 
        else:
            self._dir = scheme_data_dir 

        self._name = name
        self._check_flavour()
        self._check_mode()
        self._update_colours()
        self.save()

    @property
    def flavour(self) -> str:
        return self._flavour

    @flavour.setter
    def flavour(self, flavour: str) -> None:
        if flavour == self._flavour:
            return

        if flavour not in get_scheme_flavours():
            if self.notify:
                notify(
                    "-u",
                    "critical",
                    "Unable to set scheme flavour",
                    f'"{flavour}" is not a valid flavour of scheme "{self.name}".\n'
                    f"Valid flavours are: {get_scheme_flavours()}",
                )
            raise ValueError(f'Invalid scheme flavour: "{flavour}". Valid flavours: {get_scheme_flavours()}')

        self._flavour = flavour
        self._check_mode()
        self.update_colours()

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, mode: str) -> None:
        if mode == self._mode:
            return

        if mode not in get_scheme_modes():
            if self.notify:
                notify(
                    "-u",
                    "critical",
                    "Unable to set scheme mode",
                    f'Scheme "{self.name} {self.flavour}" does not have a {mode} mode.',
                )
            raise ValueError(f'Invalid scheme mode: "{mode}". Valid modes: {get_scheme_modes()}')

        self._mode = mode
        self.update_colours()

    @property
    def variant(self) -> str:
        return self._variant

    @variant.setter
    def variant(self, variant: str) -> None:
        if variant == self._variant:
            return

        self._variant = variant
        self.update_colours()

    @property
    def colours(self) -> dict[str, str]:
        return self._colours

    def get_colours_path(self) -> Path:
        return (self.dir / self.name / self.flavour / self.mode).with_suffix(".txt")

    @property
    def dir(self) -> Path:
        return self._dir

    def save(self) -> None:
        scheme_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_dump(
            scheme_path,
            {
                "name": self.name,
                "flavour": self.flavour,
                "mode": self.mode,
                "variant": self.variant,
                "colours": self.colours,
                "dir": str(self.dir),
            },
        )

    def set_random(self) -> None:
        schemes = get_custom_scheme_names() + get_scheme_names()

        self._name = random.choice(schemes)
        self._flavour = random.choice(get_scheme_flavours(self.dir, self.name))
        self._mode = random.choice(get_scheme_modes(self.dir, self.name, self.flavour))
        self.update_colours()

    def update_colours(self) -> None:
        self._update_colours()
        self.save()

    def _check_flavour(self) -> None:
        flavours = get_scheme_flavours(self.dir, self.name)
        if self._flavour not in flavours:
            self._flavour = flavours[0]

    def _update_path(self) -> None:
        self._path = get_scheme_dir(self.name)

    def _check_mode(self) -> None:
        modes = get_scheme_modes(self.dir, self.name, self.flavour)
        if self._mode not in modes:
            self._mode = modes[0]

    def _update_colours(self) -> None:
        if self.name == "dynamic":
            from caelestia.utils.material import get_colours_for_image

            try:
                self._colours = get_colours_for_image()
            except FileNotFoundError:
                if self.notify:
                    notify(
                        "-u",
                        "critical",
                        "Unable to set dynamic scheme",
                        "No wallpaper set. Please set a wallpaper via `caelestia wallpaper` before setting a dynamic scheme.",
                    )
                raise ValueError(
                    "No wallpaper set. Please set a wallpaper via `caelestia wallpaper` before setting a dynamic scheme."
                )
        else:
            self._colours = read_colours_from_file(self.get_colours_path())

    def __str__(self) -> str:
        return (
            f"Current scheme:\n"
            f"    Name: {self.name}\n"
            f"    Flavour: {self.flavour}\n"
            f"    Mode: {self.mode}\n"
            f"    Variant: {self.variant}\n"
            f"    Dir: {self.dir}\n"
            f"    Colours:\n"
            f"        {'\n        '.join(f'{n}: \x1b[38;2;{int(c[0:2], 16)};{int(c[2:4], 16)};{int(c[4:6], 16)}m{c}\x1b[0m' for n, c in self.colours.items())}"
        )


scheme_variants = [
    "tonalspot",
    "vibrant",
    "expressive",
    "fidelity",
    "fruitsalad",
    "monochrome",
    "neutral",
    "rainbow",
    "content",
]

scheme: Scheme | None = None


def read_colours_from_file(path: Path) -> dict[str, str]:
    return {
        k.strip(): v.strip().removeprefix("#")
        for k, v in (line.split(" ") for line in path.read_text().splitlines() if line)
    }


def get_scheme_path() -> Path:
    return get_scheme().get_colours_path()

def get_scheme_dir(name: str | None = None) -> Path:
    if name is None:
        name = get_scheme().name
    return user_schemes_dir if name in get_custom_scheme_names() else scheme_data_dir


def get_scheme() -> Scheme:
    global scheme

    if scheme is None:
        try:
            scheme_json = json.loads(scheme_path.read_text())
            scheme = Scheme(scheme_json)
        except (IOError, json.JSONDecodeError):
            scheme = Scheme(None)
            scheme.save()

    return scheme


def get_scheme_names() -> list[str]:
    return [*(f.name for f in scheme_data_dir.iterdir() if f.is_dir()), "dynamic"]

def get_custom_scheme_names() -> list[str]:
    if not user_schemes_dir.is_dir():
        return []
    return [f.name for f in user_schemes_dir.iterdir() if f.is_dir()]

def get_scheme_flavours(dir: Path | None = None, name: str | None = None) -> list[str]:
    if name is None or dir is None:
        scheme = get_scheme()
        name = scheme.name
        dir = scheme.dir

    return (
        ["default", "hard"] if name == "dynamic" else [f.name for f in (dir / name).iterdir() if f.is_dir()]
    )


def get_scheme_modes(dir: Path | None = None, name: str | None = None, flavour: str | None = None) -> list[str]:
    if dir is None or name is None or flavour is None:
        scheme = get_scheme()
        dir = scheme.dir
        name = name or scheme.name
        flavour = flavour or scheme.flavour

    if name == "dynamic":
        return ["light", "dark"]
    else:
        return [f.stem for f in (dir / name / flavour).iterdir() if f.is_file()]

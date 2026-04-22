from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload

type PathLike = str | Path
type Kind = Literal["dir", "file"]


class PathsError(Exception):
    """Base exception for path-schema related errors."""


class MissingPathError(PathsError, FileNotFoundError):
    """Raised when a required path does not exist."""


class WrongPathTypeError(PathsError):
    """Raised when a path exists but is not the expected type."""


def ensure(path: PathLike, kind: Kind = "dir") -> Path:
    path = Path(path)
    if kind == "dir":
        path.mkdir(parents=True, exist_ok=True)
    elif kind == "file":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    else:
        raise ValueError(f"Unknown path kind: {kind!r}")
    return path


def require(path: PathLike, kind: Kind = "dir") -> Path:
    path = Path(path)
    if not path.exists():
        raise MissingPathError(f"Required path does not exist: {path}")

    if kind == "dir" and not path.is_dir():
        raise WrongPathTypeError(f"Expected directory but found: {path}")

    if kind == "file" and not path.is_file():
        raise WrongPathTypeError(f"Expected file but found: {path}")

    return path


@dataclass(frozen=True)
class PathRef:
    path: Path
    kind: Kind = "dir"  # "dir" or "file"

    def ensure(self) -> Path:
        return ensure(self.path, self.kind)

    def require(self) -> Path:
        return require(self.path, self.kind)

    # mirror common Path methods for convenience
    def exists(self) -> bool:
        return self.path.exists()

    def is_file(self) -> bool:
        return self.path.is_file()

    def is_dir(self) -> bool:
        return self.path.is_dir()

    def joinpath(self, *parts: PathLike) -> Path:
        return self.path.joinpath(*parts)

    def with_suffix(self, suffix: str) -> Path:
        return self.path.with_suffix(suffix)

    def relative_to(self, other: PathLike) -> Path:
        return self.path.relative_to(other)

    # what should "a / b" syntax mean? Same as for Path and return Path
    def __truediv__(self, other: PathLike) -> Path:
        return self.path / other

    # file system path protocol, so that PathRef can be used directly in APIs expecting paths
    def __fspath__(self) -> str:
        return str(self.path)

    # string representation for debugging
    def __str__(self) -> str:
        return str(self.path)


@dataclass(frozen=True)
class PathField[T]:
    """
    Descriptor for declaring a structured path on a PathsBase object.

    The wrapped function should return a concrete Path.
    Access through an instance returns a PathRef.
    Access through the class returns the descriptor itself.
    """

    factory: Callable[[T], Path]
    kind: Kind = "dir"

    # set attribute name
    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "name", name)

    # for type checking: envoking __get__ ("a.b") can return either the descriptor or the PathRef
    # if obj is None, return self
    @overload
    def __get__(self, obj: None, owner: type | None = ...) -> PathField[T]: ...

    # if obj is not None, return PathRef
    @overload
    def __get__(self, obj: T, owner: type | None = ...) -> PathRef: ...

    # declaration
    def __get__(
        self, obj: T | None, owner: type | None = None
    ) -> PathField[T] | PathRef:

        # If not further accessing attributes (.pathfield  --> obj = None), return the descriptor
        if obj is None:
            return self

        # If instead an attribute is accessed (.pathfield.sub --> obj = sub), return the PathRef
        return PathRef(self.factory(obj), kind=self.kind)


@dataclass(frozen=True)
class ChildPathsField[T, P]:
    """
    Descriptor for nested path namespaces.

    The wrapped function should build and return another PathsBase instance.
    The result is cached on first access.
    """

    factory: Callable[[T], P]

    def __set_name__(self, owner: type, name: str) -> None:
        object.__setattr__(self, "name", name)

    @overload
    def __get__(self, obj: None, owner: type | None = ...) -> ChildPathsField[T, P]: ...

    @overload
    def __get__(self, obj: T, owner: type | None = ...) -> P: ...

    def __get__(
        self, obj: T | None, owner: type | None = None
    ) -> ChildPathsField[T, P] | P:
        if obj is None:
            return self

        # cache the instance on the object instead of creating a new one on every access
        cache_name = f"__cached_childpaths_{self.name}"
        cached = getattr(obj, cache_name, None)
        # if not cached, set the attribute on parent
        if cached is None:
            cached = self.factory(obj)
            setattr(obj, cache_name, cached)
        return cached


# decorator for path fields, with kind argument
def path_field[T](
    *, kind: Kind = "dir"
) -> Callable[[Callable[[T], Path]], PathField[T]]:
    """
    Declare a structured path field.

    Parameters
    ----------
    kind:
        Either "dir" or "file".
    """
    if kind not in {"dir", "file"}:
        raise ValueError("kind must be either 'dir' or 'file'")

    def wrapper(func: Callable[[T], Path]) -> PathField[T]:
        return PathField(factory=func, kind=kind)

    return wrapper


# decorator for child paths fields
def child_paths[T, P: PathsBase](func: Callable[[T], P]) -> ChildPathsField[T, P]:
    """
    Declare a nested path namespace.

    Example
    -------
    class ProjectPaths(PathsBase):
        @child_paths
        def process(self) -> ProcessPaths:
            return ProcessPaths(self.base / "process")
    """
    return ChildPathsField(factory=func)


class PathsBase:
    """
    Base class for project-specific path namespaces.

    Convention:
    - `self.base` is the anchor path for the namespace
    - `@path_field(...)` declares files/directories
    - `@child_paths` declares non-parameterized nested namespaces
    """

    def __init__(self, base: PathLike) -> None:
        self.base = Path(base)

    @classmethod
    def _field_names(cls) -> list[str]:
        names: list[str] = []
        for name in dir(cls):  # recursively get names of all attributes
            attr = getattr(cls, name, None)
            if isinstance(attr, PathField):
                names.append(name)
        return names

    def describe(self) -> dict[str, PathRef]:
        """
        Return all declared path fields as a name -> PathRef mapping.
        """
        return {name: getattr(self, name) for name in self._field_names()}

    def ensure_all(self) -> None:
        """
        Ensure every declared path field exists.

        This is convenient, but can be too aggressive for some projects because
        file fields will also be touched. Use selectively if that matches your policy.
        """
        for ref in self.describe().values():
            ref.ensure()

    def require_all(self) -> None:
        """
        Require every declared path field to exist.
        """
        for ref in self.describe().values():
            ref.require()

from pathlib import Path

from stillib_paths import PathLike, PathsBase, child_paths, path_field


class RunPaths(PathsBase):
    @path_field(kind="dir")
    def root(self) -> Path:
        return self.base / "run"

    @path_field(kind="file")
    def log(self) -> Path:
        return self.root.path / "run.log"

    @path_field(kind="file")
    def result_json(self) -> Path:
        return self.root.path / "result.json"


class ProjectPaths(PathsBase):
    @path_field(kind="dir")
    def data(self) -> Path:
        return self.base / "data"

    @path_field(kind="dir")
    def artifacts(self) -> Path:
        return self.base / "artifacts"

    @path_field(kind="file")
    def config(self) -> Path:
        return self.base / "config.toml"

    @child_paths
    def run(self) -> RunPaths:
        return RunPaths(self.base)


if __name__ == "__main__":
    paths = ProjectPaths("example_project")

    print("Data dir:", paths.data)
    print("Artifacts dir:", paths.artifacts)
    print("Config file:", paths.config)

    paths.data.ensure()
    paths.artifacts.ensure()

    run = paths.run
    run.root.ensure()
    print("Run log path:", run.log)
    print("Run result path:", run.result_json)
    run.log.ensure()

    print("Run object is cached: ", paths.run is paths.run)

    print("\nDeclared project paths:")
    for name, ref in paths.describe().items():
        print(f"  {name:10s} -> {ref.path} [{ref.kind}]")

from pathlib import Path

from stillib_paths import PathLike, PathsBase, path_field


class RunPaths(PathsBase):
    # inherit base path and assign a run_name parameterically
    def __init__(self, base: PathLike, run_name: str) -> None:
        super().__init__(base)
        self.run_name = run_name

    @path_field(kind="dir")
    def root(self) -> Path:
        return self.base / "runs" / self.run_name

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

    def run(self, run_name: str) -> RunPaths:
        return RunPaths(self.base, run_name)


if __name__ == "__main__":
    paths = ProjectPaths("example_project")

    print("Data dir:", paths.data)
    print("Artifacts dir:", paths.artifacts)
    print("Config file:", paths.config)

    paths.data.ensure()
    paths.artifacts.ensure()

    run = paths.run("run_001")
    run.root.ensure()
    print("Run log path:", run.log)
    print("Run result path:", run.result_json)
    run.log.ensure()

    print("\nDeclared project paths:")
    for name, ref in paths.describe().items():
        print(f"  {name:10s} -> {ref.path} [{ref.kind}]")

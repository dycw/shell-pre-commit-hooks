from pre_commit_hooks.run_pip_compile import main

if __name__ == "__main__":
    raise SystemExit(int(not main()))

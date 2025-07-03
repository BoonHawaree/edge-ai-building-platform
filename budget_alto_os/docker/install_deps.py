import subprocess
import sys

sys.path.append('/startup')

def _install_addl_deps():
    from requirements import extras_require as extras

    addl_deps = ["web", "testing", "weather", "drivers", "databases"]
    for dep in addl_deps:
        deps_to_install = extras.get(dep, None)
        if deps_to_install is not None:
            install_cmd = ["pip3", "install"]
            install_cmd.extend(deps_to_install)
            print(f"Installing {dep} group dependencies: {deps_to_install}")
            subprocess.check_call(install_cmd)

def _install_required_deps():
    from requirements import option_requirements as opt_reqs

    for req in opt_reqs:
        package, options = req
        install_cmd = ["pip3", "install", "--no-deps"]
        if options:
            for opt in options:
                install_cmd.extend([f'--config-settings="{opt}"'])
        install_cmd.append(package)
        subprocess.check_call(install_cmd)


def _install_postgres():
    print("Installing packages for postgres")
    from requirements import extras_require as extras

    postgres_pack = extras.get("postgres", None)
    install_cmd = ["pip3", "install"]
    install_cmd.extend(postgres_pack)
    if install_cmd is not None:
        print(f"Installing packages for postgres: {postgres_pack}")
        subprocess.check_call(install_cmd)


if __name__ == "__main__":
    _install_addl_deps()
    _install_required_deps()
    _install_postgres()

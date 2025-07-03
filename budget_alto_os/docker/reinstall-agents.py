import os
import sys
import yaml
from slogger import get_logger
import subprocess

slogger = get_logger("reinstall-agents", "reinstall-agents")

VOLTTRON_CMD = "volttron"
VOLTTRON_HOME = os.environ["VOLTTRON_HOME"]
VOLTTRON_ROOT = os.environ["VOLTTRON_ROOT"]
KEYSTORES = os.path.join(VOLTTRON_HOME, "keystores")
INSTALL_PATH = "{}/scripts/install-agent.py".format(VOLTTRON_ROOT)
VOLTTRON_CTL_CMD = "volttron-ctl"

def get_platform_configurations(platform_config_path):
    with open(platform_config_path) as cin:
        config = yaml.safe_load(cin)
        agents = config["agents"]
        platform_cfg = config["config"]

    print("Platform instance name set to: {}".format(platform_cfg.get("instance-name")))

    return config, agents, platform_cfg


def get_platform_config_path():
    platform_config = None
    if "PLATFORM_CONFIG" in os.environ and os.environ["PLATFORM_CONFIG"]:
        platform_config = os.environ["PLATFORM_CONFIG"]
    elif os.path.isfile("/platform_config.yml"):
        platform_config = "/platform_config.yml"
    slogger.info(f"Platform_config: {platform_config}")

    # Stop processing if platform config hasn't been specified
    if platform_config is None:
        sys.stderr.write("No platform configuration specified.")
        slogger.debug("No platform configuration specified.")
        sys.exit(0)

    return platform_config

def install_agents(agents):
    need_to_install = {}

    sys.stdout.write("Available agents that are needing to be setup/installed")
    print(f"{agents.keys()}")

    # TODO Fix so that the agents identities are consulted.
    for identity, specs in agents.items():
        path_to_keystore = os.path.join(KEYSTORES, identity)
        if not os.path.exists(path_to_keystore):
            need_to_install[identity] = specs

    # if we need to do installs then we haven't setup this at all.
    if need_to_install:
        envcpy = os.environ.copy()
        failed_install = []
        for identity, spec in need_to_install.items():
            slogger.info("Processing identity: {}".format(identity))
            sys.stdout.write("Processing identity: {}\n".format(identity))
            if "source" not in spec:
                slogger.info(f"Invalid source for identity: {identity}")
                sys.stderr.write("Invalid source for identity: {}\n".format(identity))
                continue

            # get the source code of the agent
            agent_source = os.path.expandvars(os.path.expanduser(spec["source"]))
            if not os.path.exists(agent_source):
                slogger.info(
                    f"Invalid agent source {agent_source} for identity {identity}"
                )
                sys.stderr.write(
                    "Invalid agent source ({}) for agent id identity: {}\n".format(
                        agent_source, identity
                    )
                )
                continue

            # get agent configuration
            agent_cfg = None
            if "config" in spec and spec["config"]:
                agent_cfg = os.path.abspath(
                    os.path.expandvars(os.path.expanduser(spec["config"]))
                )
                if not os.path.exists(agent_cfg):
                    slogger.info(f"Invalid config {agent_cfg} for identity {identity}")
                    sys.stderr.write(
                        "Invalid config ({}) for agent id identity: {}\n".format(
                            agent_cfg, identity
                        )
                    )
                    continue

            # grab the priority from the system config file
            # priority = spec.get("priority", "50")
            tag = spec.get("tag", "all_agents")

            install_cmd = ["python3", INSTALL_PATH]
            install_cmd.extend(["--agent-source", agent_source])
            install_cmd.extend(["--vip-identity", identity])
            # install_cmd.extend(["--priority", priority])
            # install_cmd.extend(["--agent-start-time", AGENT_START_TIME])
            install_cmd.append("--force")
            install_cmd.extend(["--tag", tag])

            if agent_cfg:
                print(f"Using agent config: {agent_cfg}")
                install_cmd.extend(["--config", agent_cfg])

            # This allows install agent to ignore the fact that we aren't running
            # form a virtual environment.
            envcpy["IGNORE_ENV_CHECK"] = "1"
            try:
                subprocess.check_call(install_cmd, env=envcpy)
            except subprocess.CalledProcessError as e:
                # sometimes, the install command returns an Error saying that volttron couldn't install the agent, when in fact the agent was successfully installed
                # this is most likely a bug in Volttron. For now, we are ignoring that error so that the setup of the Volttron platform does not fail and to allow Docker to start the container
                sys.stderr.write(f"IGNORING ERROR: {e}")
                slogger.debug(f"IGNORING ERROR: {e}")
                failed_install.append(identity)
                continue

            if "config_store" in spec:
                sys.stdout.write("Processing config_store entries")
                for key, entry in spec["config_store"].items():
                    if "file" not in entry or not entry["file"]:
                        slogger.info(
                            f"Invalid config store entry; file must be specified for {key}"
                        )
                        sys.stderr.write(
                            "Invalid config store entry file must be specified for {}".format(
                                key
                            )
                        )
                        continue
                    entry_file = os.path.expandvars(os.path.expanduser(entry["file"]))

                    if not os.path.exists(entry_file):
                        slogger.info(
                            f"Invalid config store file not exist: {entry_file}"
                        )
                        sys.stderr.write(
                            "Invalid config store file does not exist {}".format(
                                entry_file
                            )
                        )
                        continue

                    entry_cmd = [
                        VOLTTRON_CTL_CMD,
                        "config",
                        "store",
                        identity,
                        key,
                        entry_file,
                    ]
                    if "type" in entry:
                        entry_cmd.append(entry["type"])

                    subprocess.check_call(entry_cmd)
        slogger.info(f"Agents that failed to install {failed_install}")


if __name__ == "__main__":
    config_tmp, agents_tmp, platform_cfg_tmp = get_platform_configurations(
        get_platform_config_path()
    )
    install_agents(agents_tmp)
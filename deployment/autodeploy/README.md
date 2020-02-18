
Auto-deploy and Sanity-Test script
===

This is the autodeploy script for StarlingX project.

## Get Your System Prepared

This script is tested on
* Ubunto 16.04/18.04
* Python 3.5

## Quick Start for VM Deployment

1. Install libvirt 4.0.0.

 - To install libvirt, enter folder ./libvirt/install/, and run install_packages.sh.

2. Run deployment with cmds like this:
    ```
    $ python3 autodeploy.py \
        --method vm \                  ## VM Deployment, Default
        --system_mode multi \          ## simplex|duplex|multi
        --helm_charts test.tgz \       ## amada application charts
        bootimage.iso                  ## target ISO
    ```

* Run "python3 autodeploy.py --help" to get full parameter list.
* Default test configuration is in config.json. To overwrite the config, use --config [Your Config Json]. There is an example of overwrite config json file under ./ansibleconfig folder.


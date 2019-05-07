# vuls-scan

Automatic vuls scan

## This pipeline requires a gitlab runner with the following requisites:
* expect tool, wget and sendmail installed and configured
* passwordless sudo access
* internet access
* a way to deploy automatically a Virtual Machine using StarlingX ISO
* a valid resolv.conf in the `resources` directory
    (just in case your VM has no access to internet)

## Files to be modified for your configuration
* `.gitlab-ci.yml`:
  - Add your proxies or remove them from variables
  - Add your VM's hostname or ip to the variables
* `*.expect`:
  - Adapt them to use your VM's hostname or ip
* `keys` directory
  - Fill up a pair of ssh rsa keys and name them `temp` and `temp.pub`
* `resources/resolv.conf`
  - Place a valid resolv.conf in case you need it grant you internet access
    inside your VM
* `resources/setup_env.sh`
  - Uncomment `proxy` and/or `resolv.conf` part as needed
* `resources/vuls.sh`
  - Uncomment `proxy` as required

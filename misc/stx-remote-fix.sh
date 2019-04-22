#!/bin/bash
# stx-remote-fix.sh Update git remotes for OpenDev rename
#
# stx-remote-fix.sh [-n|--dry-run]
#
# Run in the root of a git repo
#
# Search git remotes for updates due to the OpenDev transition:
#
# git.openstack.org         opendev.org
# review.openstack.org      review.opendev.org
# /openstack-dev/           /openstack/
# /openstack-infra/         /openstack/
# git.starlingx.io/stx      opendev.org/starlingx/
# /openstack/stx-           /starlingx/
# github.com/openstack      review.opendev.org/openstack

DRY_RUN=""
if [[ "$1" == "--dry-run" || "$1" == "-n" ]]; then
    DRY_RUN=echo
fi

# Get remotes
git remote -v | grep "\(fetch\)" | while read name url _; do
    new_url=$(echo $url | sed "
        s|git.openstack.org|opendev.org|;
        s|review.openstack.org|review.opendev.org|;
        s|/openstack-dev/|/openstack/|;
        s|/openstack-infra/|/openstack/|;
        s|git.starlingx.io/stx-|opendev.org/starlingx/|;
        s|/openstack/stx-|/starlingx/|;
        s|github.com/openstack|review.opendev.org/openstack|;
    ")

    # Recreate git remotes
    if [[ "$new_url" != "$url" ]]; then
        echo "$name $new_url"
        $DRY_RUN git remote set-url $name $new_url
    fi
done

#!/bin/bash

set -ex

function submit() {
    bkr job-submit - <<EOF
<job retention_tag="scratch">
    <whiteboard>
        custom kickstart
    </whiteboard>
    <recipeSet>
        <recipe>
            <distroRequires>
                <and>
                    <distro_arch op="=" value="x86_64"/>
                    <distro_family op="=" value="RedHatEnterpriseLinux6"/>
                    <distro_variant op="=" value="Server"/>
                </and>
            </distroRequires>
            <hostRequires>
                <hostname op="=" value="$TEST_SYSTEM" />
            </hostRequires>
            <task name="/distribution/install" role="STANDALONE">
                <params/>
            </task>
        </recipe>
    </recipeSet>
</job>
EOF
}

job_id=$(submit | awk -F\' '{print $2}')
bkr job-watch $job_id
wget -nv -O kickstart.actual "http://$SERVERS/cblr/svc/op/ks/system/$TEST_SYSTEM"
rhts-submit-log -l kickstart.actual
# We could diff this against an expected kickstart, like this...
#diff -u kickstart.expected kickstart.actual
# We would get an exit status of 1 if there were some difference.
# But the kickstart has lots of site-specific stuff in it (distro paths etc)
# so that's not really practical. :-(
# We can at least check for the absence of our magical %post command:
if grep -q '^echo hello$' kickstart.actual ; then exit 1 ; fi

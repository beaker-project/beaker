#!/bin/bash

# Builds a development (S)RPM from HEAD.

set -e

if [ $# -eq 0 ] ; then
    echo "Usage: $1 -bs|-bb <rpmbuild-options...>" >&2
    echo "Hint: -bs builds SRPM, -bb builds RPM, refer to rpmbuild(8)" >&2
    exit 1
fi

tag="$(git describe --match=beaker-0\* --abbrev=0 HEAD)"
version="${tag##beaker-}"
commitcount=$(git rev-list "$tag..HEAD" | wc -l)
commitsha=$(git rev-parse --short HEAD)
if [ "$commitcount" -gt 0 ] ; then
    # git builds count as a pre-release of the next version
    rpmver="${version%.*}.$((${version##*.} + 1))"
    rpmrel="0.git.${commitcount}.${commitsha}"
    version="${version%.*}.$((${version##*.} + 1)).git.${commitcount}.${commitsha}"
fi

workdir="$(mktemp -d)"
trap "rm -rf $workdir" EXIT
outdir="$(readlink -f ./rpmbuild-output)"
mkdir -p "$outdir"

git archive --format=tar --prefix="beaker-${version}/" HEAD | gzip >"$workdir/beaker-${version}.tar.gz"
git show HEAD:beaker.spec >"$workdir/beaker.spec"

if [ "$commitcount" -gt 0 ] ; then
    # need to hack the spec
    sed --regexp-extended --in-place \
        -e "/%global upstream_version /c\%global upstream_version ${version}" \
        -e "/^Version:/cVersion: ${rpmver}" \
        -e "/^Release:/cRelease: ${rpmrel}%{?dist}" \
        "$workdir/beaker.spec"
fi

# We force the use of md5 hashes for RHEL5 compatibility
rpmbuild \
    --define "_source_filedigest_algorithm md5" \
    --define "_binary_filedigest_algorithm md5" \
    --define "_topdir $workdir" \
    --define "_sourcedir $workdir" \
    --define "_specdir $workdir" \
    --define "_rpmdir $outdir" \
    --define "_srcrpmdir $outdir" \
    "$@" "$workdir/beaker.spec"

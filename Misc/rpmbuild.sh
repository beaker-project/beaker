#!/bin/bash

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Builds a development (S)RPM from HEAD.

set -e

if [[ "$1" == "--next-major" ]] ; then
    next_major=1
    shift
fi

if [ $# -eq 0 ] ; then
    echo "Usage: $1 -bs|-bb <rpmbuild-options...>" >&2
    echo "Hint: -bs builds SRPM, -bb builds RPM, refer to rpmbuild(8)" >&2
    exit 1
fi

lasttag="$(git describe --abbrev=0 HEAD)"
lastversion="${lasttag##beaker-}"
if [ "$(git rev-list "$lasttag..HEAD" | wc -l)" -eq 0 ] ; then
    # building a tag
    rpmver=""
    rpmrel=""
    version="$lastversion"
else
    # git builds count as a pre-release of the next version
    version="$lastversion"
    version="${version%%[a-z]*}" # strip non-numeric suffixes like "rc1"
    if [ -z "$next_major" ] ; then
        # normally we just increment the last portion of the version
        version="${version%.*}.$((${version##*.} + 1))"
    else
        # ... but if --next-major is given we increment the first portion
        version="$((${version%%.*} + 1)).0"
        # also count commits from the last *major* version, so that the number 
        # does not go down when a new maintenance release is tagged
        lastversion="${lastversion%%.*}.0"
    fi
    commitcount=$(git rev-list "beaker-$lastversion..HEAD" | wc -l)
    commitsha=$(git rev-parse --short HEAD)
    rpmver="${version}"
    rpmrel="0.git.${commitcount}.${commitsha}"
    version="${version}.git.${commitcount}.${commitsha}"
fi

workdir="$(mktemp -d)"
trap "rm -rf $workdir" EXIT
outdir="$(readlink -f ./rpmbuild-output)"
mkdir -p "$outdir"

git archive --format=tar --prefix="beaker-${version}/" HEAD | xz >"$workdir/beaker-${version}.tar.xz"
git ls-tree -r HEAD | grep ^160000 | while read mode type sha path ; do
    # for submodules we produce a tar archive that mimics the style of the 
    # GitHub archives we are expecting in the RPM build
    (cd $path && git archive --format=tar --prefix="$(basename $path)-$sha/" $sha) | gzip >"$workdir/$(basename $path)-$sha.tar.gz"
done
git show HEAD:beaker.spec >"$workdir/beaker.spec"

if [ -n "$rpmrel" ] ; then
    # need to hack the version in the spec
    sed --regexp-extended --in-place \
        -e "/%global upstream_version /c\%global upstream_version ${version}" \
        -e "/^Version:/cVersion: ${rpmver}" \
        -e "/^Release:/cRelease: ${rpmrel}%{?dist}" \
        "$workdir/beaker.spec"
    # inject %prep commands to also hack the Python module versions
    # (beware the precarious quoting here...)
    commands=$(cat <<EOF
sed -i -e "/version=/c\\\\    version='$version$prerelease'," */setup.py
sed -i -e "/__version__/c\\\\__version__ = '$version$prerelease'" Common/bkr/common/__init__.py
EOF
)
    awk --assign "commands=$commands" \
        '{ print } ; /^%setup/ { print commands }' \
        "$workdir/beaker.spec" >"$workdir/beaker.spec.injected"
    mv "$workdir/beaker.spec.injected" "$workdir/beaker.spec"
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

import re
import shutil
from tito.common import debug, run_command
from tito.tagger import VersionTagger
from tito.builder import Builder, UpstreamBuilder

class BeakerVersionTagger(VersionTagger):
    """
    VersionTagger with changelog customised for Beaker's peculiar requirements.

    Note that the customisations in this subclass will only take effect when 
    using tito >= 0.3.1.
    """

    def _generate_default_changelog(self, last_tag):
        # Grab all the commits we are interested in
        commits = run_command('git log --pretty=format:%%H --relative %s..HEAD -- .'
                % last_tag)

        changelog = []
        for sha in reversed(commits.split('\n')):
            subject = run_command('git show -s --pretty="format:%s" %s'
                    % (self._changelog_format(), sha))

            # Skip Gerrit merges
            if re.match(r'Merge ".*" into', subject):
                continue

            # Skip Tito version bumps
            if re.match(r'Automatic commit of package \[.*\] release \[.*\]', subject):
                continue

            # Tito's built-in cherry-pick cleaning
            subject = self._changelog_remove_cherrypick(subject)

            # Check for Bug: footer
            body = run_command('git show -s --pretty=format:%%b %s' % sha)
            m = re.search(r'^Bug:\s*(\d+)', body, re.IGNORECASE | re.MULTILINE)
            if m:
                bz_number = m.group(1)
                subject = '%s %s' % (bz_number, subject)

            # Escape rpm macros
            subject = subject.replace('%', '%%')

            changelog.append(subject)
        return '\n'.join(changelog)

BAD_TAGS = [
    'beaker-0.8.0-24.1', # divergent
]

class BeakerBuilder(UpstreamBuilder):

    # So much hackery... tito's Builders have a weird inheritance hierarchy

    def tgz(self):
        if self.test:
            Builder.tgz(self)
        else:
            UpstreamBuilder.tgz(self)
            shutil.copy('%s/%s' % (self.rpmbuild_sourcedir, self.tgz_filename),
                    self.rpmbuild_basedir)
            print 'Wrote: %s/%s' % (self.rpmbuild_basedir, self.tgz_filename)

    def _setup_test_specfile(self):
        if self.test:
            Builder._setup_test_specfile(self)
        else:
            UpstreamBuilder._setup_test_specfile(self)

    def patch_upstream(self):
        commits = run_command('git rev-list --reverse %s..%s -- .'
                % (self.upstream_tag, self.git_commit_id))
        patch_filenames = []
        previous_tag = self.upstream_tag
        for commit in commits.splitlines():
            tag = run_command('git describe --tags --match %s-%s\\* --exact-match %s 2>/dev/null || :'
                    % (self.project_name, self.upstream_version, commit))
            if tag and tag not in BAD_TAGS:
                self._generate_patch(previous_tag, tag, '%s.patch' % tag)
                patch_filenames.append('%s.patch' % tag)
                previous_tag = tag
        if self.test:
            # If this is a --test build, there will be some untagged commits at
            # the end which we also need to include.
            self._generate_patch(previous_tag, self.git_commit_id, '%s.patch' % self.display_version)
            patch_filenames.append('%s.patch' % self.display_version)
        else:
            assert previous_tag == self.build_tag or not commits

        (patch_number, patch_insert_index, patch_apply_index, lines) = self._patch_upstream()
        for patch in patch_filenames:
            lines.insert(patch_insert_index, "Patch%s: %s\n" % (patch_number, patch))
            lines.insert(patch_apply_index, "%%patch%s -p1\n" % (patch_number))
            patch_number += 1
            patch_insert_index += 1
            patch_apply_index += 2
        self._write_spec(lines)

    def _generate_patch(self, left, right, out):
        # It's nice to publish patches which show the actual commits making up
        # the patch, with authorship, dates, log messages, etc.
        # We can use git log for that. But it will only produce usable patches if
        # left is an ancestor of every commit in left..right.
        # That will normally be true for a series of hotfixes on top of a
        # release. But if we are doing a --test build or if there are divergent
        # tags then this might not be true. In that case the best we can do is
        # git diff left..right.
        if not run_command('git rev-list $(git rev-list --first-parent %s..%s | tail -n1)..%s'
                % (left, right, left)):
            print 'Generating patchset %s..%s' % (left, right)
            run_command('git log -p --reverse --pretty=email '
                    '-m --first-parent '
                    '--no-renames ' # patch can't handle these :-(
                    '--relative %s..%s -- . >%s/%s'
                    % (left, right, self.rpmbuild_gitcopy, out))
        else:
            print 'Generating diff %s..%s' % (left, right)
            run_command('git diff --no-renames '
                    '--relative %s..%s -- . >%s/%s'
                    % (left, right, self.rpmbuild_gitcopy, out))
        shutil.copy('%s/%s' % (self.rpmbuild_gitcopy, out), self.rpmbuild_sourcedir)
        shutil.copy('%s/%s' % (self.rpmbuild_gitcopy, out), self.rpmbuild_basedir)
        print 'Wrote: %s/%s' % (self.rpmbuild_basedir, out)

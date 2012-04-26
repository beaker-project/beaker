import re
from tito.common import run_command
from tito.tagger import VersionTagger

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
            subject = run_command('git show -s --pretty="format:%%s%s" %s'
                    % (self._changelog_email(), sha))

            # Skip Gerrit merges
            if re.match(r'Merge ".*" into develop', subject):
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

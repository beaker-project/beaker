# Makefile for Sphinx documentation
#

# Python 2 default
ifeq ($(BKR_PY3),)
	BKR_PY3 :=0
endif

python_command :=  $(shell if [[ $(BKR_PY3) == 0 ]]; then echo "python2"; else echo "python3"; fi)
python_path :=  $(shell if [[ $(BKR_PY3) == 0 ]]; then echo "../Common:../Server:../Client/src"; else echo "../Common:../Client/src"; fi)
bkr_path_injected :=  $(shell if [[ $(BKR_PY3) == 0 ]]; then echo \"../Common/bkr\", \"../Server/bkr\", \"../Client/src/bkr\"; else echo \"../Common/bkr\", \"../Client/src/bkr\"; fi)
SHELL = /bin/bash
export PYTHONPATH=$(python_path)
SPHINXBUILD ?= $(firstword $(shell command -v sphinx-1.0-build sphinx-build))

# This Makefile contains some frustrating hacks, centering around the fact that
# the docs use autodoc and therefore need to be able to import bkr modules from
# the source tree which they live inside.
#
# pkg_resources.requires() does not work if multiple versions are installed in
# parallel, but we need to be able to load bkr for autodoc generation. The
# semi-supported hack using __requires__ in the $SPHINXBUILD definition
# is a workaround: http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
# (EPEL6 has python-sphinx = 0.6 and python-sphinx10 = 1.0)
#
# In addition, if the pkg_resources dependency chain includes anything which
# needs to be added to sys.path *and* anything which is in site-packages, then
# site-packages gets prepended to sys.path in front of anything we pass in
# through PYTHONPATH. That means, if you have bkr in site-packages it will be
# imported instead of the local source. To work around the pkg_resources
# behaviour we have to fiddle with bkr.__path__ ourselves in addition to
# setting PYTHONPATH.
#
# Also see: https://bitbucket.org/pypa/setuptools/issue/6/

SPHINXREQUIRES = "Sphinx >= 1.0",
ifeq (0,$(shell $(python_command) -c '__requires__ = ["CherryPy < 3.0"]; import pkg_resources' &>/dev/null ; echo $$?))
    SPHINXREQUIRES += "CherryPy < 3.0",
endif
BKR_PATH_INJECTED = $(bkr_path_injected)

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD  := $(python_command) -c '__requires__ = [$(SPHINXREQUIRES)]; import pkg_resources; \
    import bkr; bkr.__path__ = [$(BKR_PATH_INJECTED)]; \
    exec(open("$(SPHINXBUILD)").read())'
PAPER         =
BUILDDIR      = _build

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: build
build: man text

.PHONY: install
install: man
	install -m0755 -d $(DESTDIR)/usr/share/man/man{1,8}
	install -m0644 _build/man/*.1 $(DESTDIR)/usr/share/man/man1
	if [[ ${BKR_PY3} == 0 ]]; then \
		install -m0644 _build/man/*.8 $(DESTDIR)/usr/share/man/man8; \
	fi
	ln -s bkr-distro-trees-verify.1.gz $(DESTDIR)/usr/share/man/man1/bkr-distros-verify.1.gz
	ln -s bkr-system-list.1.gz $(DESTDIR)/usr/share/man/man1/bkr-list-systems.1.gz
	ln -s bkr-labcontroller-list $(DESTDIR)/usr/share/man/man1/bkr-list-labcontrollers.1.gz

.PHONY: check

.PHONY: help clean html dirhtml singlehtml pickle json htmlhelp qthelp devhelp epub latex latexpdf text man changes linkcheck doctest gettext

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html       to make standalone HTML files"
	@echo "  dirhtml    to make HTML files named index.html in directories"
	@echo "  singlehtml to make a single large HTML file"
	@echo "  pickle     to make pickle files"
	@echo "  json       to make JSON files"
	@echo "  htmlhelp   to make HTML files and a HTML help project"
	@echo "  qthelp     to make HTML files and a qthelp project"
	@echo "  devhelp    to make HTML files and a Devhelp project"
	@echo "  epub       to make an epub"
	@echo "  latex      to make LaTeX files, you can set PAPER=a4 or PAPER=letter"
	@echo "  latexpdf   to make LaTeX files and run them through pdflatex"
	@echo "  text       to make text files"
	@echo "  man        to make manual pages"
	@echo "  texinfo    to make Texinfo files"
	@echo "  info       to make Texinfo files and run them through makeinfo"
	@echo "  gettext    to make PO message catalogs"
	@echo "  changes    to make an overview of all changed/added/deprecated items"
	@echo "  linkcheck  to check all external links for integrity"
	@echo "  doctest    to run all doctests embedded in the documentation (if enabled)"

clean:
	-rm -rf $(BUILDDIR)/*

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

dirhtml:
	$(SPHINXBUILD) -b dirhtml $(ALLSPHINXOPTS) $(BUILDDIR)/dirhtml
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/dirhtml."

singlehtml:
	$(SPHINXBUILD) -b singlehtml $(ALLSPHINXOPTS) $(BUILDDIR)/singlehtml
	@echo
	@echo "Build finished. The HTML page is in $(BUILDDIR)/singlehtml."

pickle:
	$(SPHINXBUILD) -b pickle $(ALLSPHINXOPTS) $(BUILDDIR)/pickle
	@echo
	@echo "Build finished; now you can process the pickle files."

json:
	$(SPHINXBUILD) -b json $(ALLSPHINXOPTS) $(BUILDDIR)/json
	@echo
	@echo "Build finished; now you can process the JSON files."

htmlhelp:
	$(SPHINXBUILD) -b htmlhelp $(ALLSPHINXOPTS) $(BUILDDIR)/htmlhelp
	@echo
	@echo "Build finished; now you can run HTML Help Workshop with the" \
	      ".hhp project file in $(BUILDDIR)/htmlhelp."

qthelp:
	$(SPHINXBUILD) -b qthelp $(ALLSPHINXOPTS) $(BUILDDIR)/qthelp
	@echo
	@echo "Build finished; now you can run "qcollectiongenerator" with the" \
	      ".qhcp project file in $(BUILDDIR)/qthelp, like this:"
	@echo "# qcollectiongenerator $(BUILDDIR)/qthelp/BeakerAdministrationGuide.qhcp"
	@echo "To view the help file:"
	@echo "# assistant -collectionFile $(BUILDDIR)/qthelp/BeakerAdministrationGuide.qhc"

devhelp:
	$(SPHINXBUILD) -b devhelp $(ALLSPHINXOPTS) $(BUILDDIR)/devhelp
	@echo
	@echo "Build finished."
	@echo "To view the help file:"
	@echo "# mkdir -p $$HOME/.local/share/devhelp/BeakerAdministrationGuide"
	@echo "# ln -s $(BUILDDIR)/devhelp $$HOME/.local/share/devhelp/BeakerAdministrationGuide"
	@echo "# devhelp"

epub:
	$(SPHINXBUILD) -b epub $(ALLSPHINXOPTS) $(BUILDDIR)/epub
	@echo
	@echo "Build finished. The epub file is in $(BUILDDIR)/epub."

latex:
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) $(BUILDDIR)/latex
	@echo
	@echo "Build finished; the LaTeX files are in $(BUILDDIR)/latex."
	@echo "Run \`make' in that directory to run these through (pdf)latex" \
	      "(use \`make latexpdf' here to do that automatically)."

latexpdf:
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) $(BUILDDIR)/latex
	@echo "Running LaTeX files through pdflatex..."
	$(MAKE) -C $(BUILDDIR)/latex all-pdf
	@echo "pdflatex finished; the PDF files are in $(BUILDDIR)/latex."

text:
	@echo "For 'Unknown node: container', see https://bitbucket.org/birkenfeld/sphinx/issue/1018/"
	$(SPHINXBUILD) -b text $(ALLSPHINXOPTS) $(BUILDDIR)/text
	@echo
	@echo "Build finished. The text files are in $(BUILDDIR)/text."

man:
	$(SPHINXBUILD) -b man $(ALLSPHINXOPTS) $(BUILDDIR)/man
	@echo
	@echo "Build finished. The manual pages are in $(BUILDDIR)/man."

texinfo:
	$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) $(BUILDDIR)/texinfo
	@echo
	@echo "Build finished. The Texinfo files are in $(BUILDDIR)/texinfo."
	@echo "Run \`make' in that directory to run these through makeinfo" \
	      "(use \`make info' here to do that automatically)."

info:
	$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) $(BUILDDIR)/texinfo
	@echo "Running Texinfo files through makeinfo..."
	make -C $(BUILDDIR)/texinfo info
	@echo "makeinfo finished; the Info files are in $(BUILDDIR)/texinfo."

gettext:
	$(SPHINXBUILD) -b gettext $(I18NSPHINXOPTS) $(BUILDDIR)/locale
	@echo
	@echo "Build finished. The message catalogs are in $(BUILDDIR)/locale."

changes:
	$(SPHINXBUILD) -b changes $(ALLSPHINXOPTS) $(BUILDDIR)/changes
	@echo
	@echo "The overview file is in $(BUILDDIR)/changes."

linkcheck:
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) $(BUILDDIR)/linkcheck
	@echo
	@echo "Link check complete; look for any errors in the above output " \
	      "or in $(BUILDDIR)/linkcheck/output.txt."

doctest:
	$(SPHINXBUILD) -b doctest $(ALLSPHINXOPTS) $(BUILDDIR)/doctest
	@echo "Testing of doctests in the sources finished, look at the " \
	      "results in $(BUILDDIR)/doctest/output.txt."

devel:
	@echo "nothing needed for devel target in documentation"

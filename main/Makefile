# Build the paper. On Gilbreth: module load texlive/20220321 first.
main.pdf: main.tex refs.bib $(wildcard sections/*.tex)
	pdflatex -interaction=nonstopmode -halt-on-error main
	bibtex main
	pdflatex -interaction=nonstopmode -halt-on-error main
	pdflatex -interaction=nonstopmode -halt-on-error main

clean:
	rm -f main.aux main.bbl main.blg main.log main.out main.pdf

.PHONY: clean

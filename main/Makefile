# Build the paper and its separately submitted appendix. On Gilbreth: module load texlive/20220321 first.
# main.tex and appendix.tex reference each other's labels (xr-hyper), so each needs the other's .aux.
SRC = preamble.tex refs.bib $(wildcard sections/*.tex)

all: main.pdf appendix.pdf

main.pdf appendix.pdf &: main.tex appendix.tex $(SRC)
	pdflatex -interaction=nonstopmode -halt-on-error main
	pdflatex -interaction=nonstopmode -halt-on-error appendix
	bibtex main
	pdflatex -interaction=nonstopmode -halt-on-error main
	pdflatex -interaction=nonstopmode -halt-on-error main
	pdflatex -interaction=nonstopmode -halt-on-error appendix

clean:
	rm -f main.aux main.bbl main.blg main.log main.out main.pdf
	rm -f appendix.aux appendix.log appendix.out appendix.pdf

.PHONY: all clean

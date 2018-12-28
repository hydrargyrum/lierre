
SOURCES=$(wildcard *.ui)
DESTS=$(SOURCES:%.ui=%_ui.py)

all: $(DESTS)

%_ui.py: %.ui
	pyuic5 "$^" -o "$@"

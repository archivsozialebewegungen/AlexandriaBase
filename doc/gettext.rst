Using and running `gettext`
###########################

Install package `gettext` (contains `xgettext`) and `poedit`.

Change into the workspace directory.

Call the following commandline:

    xgettext --language=Python --keyword=_ --output=AlexandriaGui/tkgui/locale/alexandriagui.pot `find AlexandriaGui -name "*.py"`
    xgettext --language=Python --keyword=_ --output=AlexandriaBase/alexandriabase/locale/alexandriabase.pot `find AlexandriaBase/alexandriabase -name "*.py"`

This creates a template file in AlexandriaGui/tkgui/locale named alexandriagui.pot
and a file in AlexandriaBase/alexandriabase/locale named alexandriabase.pot.

Now create a directory for your language, for example `AlexandriaGui/tkgui/locale/de` for
german and a subdirectory LC_MESSAGES. Now start `poedit`. On the start screen
select creation of a new translation. You will be asked to select the language
and the catalog file. Save the now created `de.po` file in the directory
`de/LC_MESSAGES` as `alexandria.po`. Now you may translate the messages.

If the strings in the code change, you have to recreate the `*.pot` files.
Now open you translation `*.po` files and select under the `catalog`
menu entry the option to update from POT file. Adjust the translations.
Dialog design
#############

Quick Howto
***********

- Create 3 classes: presenter, view, dialog window

   - Presenter inherits from AbstractInputDialogPresenter

   - View inherits from AbstractInputDialog

   - Dialog may inherit from InputDialogWindow, but may by any Pmw.Dialog

-  In the presenter implement the method `assemble_return_value` which
   sets the `return_value` property of the view class.

-  In the view implement the method `_init_dialog` which instantiates
   and configures its
   dialog property. It has at least the named parameter `master`, but
   may have more parameters. This method will be called when the `activate`
   method of the view is called. This method gets at least the master window
   as parameter, but may get more parameters.

-  In the view create a property `input` that returns the input the user has
   given in the input window. This property should be used by the presenter
   to get the immediate input before doing validation and stuff. More complex
   dialogs may use more complicated mechanisms, but the view should always provide
   properties for the presenter to fetch the user input.

-  Since view class and dialog window are closely coupled, only the presenter
   is injected into the view class. The dialog window class is instantiated
   within the view. It is up to the developer, if the dialog view class will
   cache the dialog window instance or create it new for each activation call
   on the view.

The concept
***********

Dialogs are a bit tricky. There are several requirements:

-  they should be injectable into other components so that their
   implementation may freely change

-  they should block all data input into the master component
   that calls the dialog

-  they themselves should have a presenter class injected that
   does all the domain logic stuff without knowing anything about
   the graphical user interface itself, so it could be tested in
   unit or integration tests

To provide this, a dialog consists of three classes: First the
dialog class itself, that is injected in some component. This
class has an `activate` method, which takes the master window
as a first parameter and any number of additional parameters
that are needed to initalize the dialog. These vary from dialog
to dialog.

The constructor of the dialog takes a presenter. The presenter
reads data from the dialog and it writes data to the dialog. It
must implement the method `assemble_return_value` and set the
return value on the dialog. This is also the hook for input
validation. This method may alternatively set the `errormessage`
property on the view, then the dialog will not be closed but
the errormessage shown.

Besides the dialog and the presenter classes there is the actual
gui class that interacts with the user. This class will be
assembled and initalized when the `activate` method on the
dialog is called. The reason for this delayed initialization
is the need to initialize the dialog by the DI container at a
moment when the context of the dialog is not yet known. This
context is provided when the `activate` method is called an the
master window is given to the dialog class.

So we have three classes, the dialog class, the presenter and the
dialog window. For all these classes exist abstract base classes that
provide functionality. The abstract base class for dialog classes is
AbstactInputDialog, for presenters AbstractInputDialogPresenter. These
should always be used when constructing a dialog. Then there
is also an InputDialogWindow class that may be used for simple dialogs.
But this is just a convenient Pmw.Dialog subclass already with OK and
Cancel buttons and an errormessage property.

The child classes of the AbstractInputDialog class must implement the
method `_init_dialog(master, *params)` to set the dialog property to
some kind of a Pwm.Dialog object.
that is used for user interaction.
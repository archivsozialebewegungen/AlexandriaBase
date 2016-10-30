The data - view - presenter pattern
###################################


There are quite some misconceptions about the so called model - view -
controller pattern. Martin Fowler has written an (aborted) article
on this theme that is quite interesting. A lot of thoughts on the
design of Alexandriaare derived from this article, although I won't
follow any of the described patterns. Why this is so is the purpose
of this text.

MVC as commonly (mis-)understood
********************************

Most conceptions of MVC is that there is some piece of software that
controlls all the data flow of the application - the controller.
The controller obtains data from some repository - the so called model.
And it makes this data known to the graphical user interface, so
it can be displayed to the user. When when the user does something
in the view, events occur and these events are propagated to the
controller. He then may or may not do something with the model according
to the state of the view.

One problem of this is that the model data exists not only once, but two
times (three times, if one is precise): Once in the controls of the view,
once in the model objects (and normally a third time in some sort of
persistance store).

Now to keep this data consistent is quite a task. So many GUI frameworks
have some data binding mechanism to bind the model data to the view
controls and vice versa. So every time, one side changes, the other
side reflects this change. So data binding is a first step so simplify
the task of the gui architect. He needs not to design a way to keep
the data objects and the view synchronized.

But in reality data binding is not really the solution. First of all it
is not a solution for use. Since Alexandria uses the tkinter wrapper of
Tcl/TK for Python, data binding does not work exceptionally well. You
need to create special variables for data binding, so you can't bind
your model data directly to the view. So this results again in having
the the data two times in the application and the need for synchronization.
But this is just a peculiarity of Python/tkinter.

The main problem of data binding is that you have to display data that
is not part of your domain model. For example results of calculations
that you want to display to the user, but that are just temporary data
you want to push to the view. Or messages. There is quite a lot of
this type of data flowing around in a gui application. To solve this
problem there often is the solution of so called "view objects" that
get constructed on top of the domain objects (mostly using the
decorator pattern) that incorporate more properties than the actual
domain objects, for example the result of a calculation.

But the use of view objects is not very satisfying. It bloats the
number of data objects in your application, it leads to inserting
a facade layer on top of your domain logic to build the view objects
from your domain objects. In short: It makes you application more
complex than necessary.

This is certainly a viable solution in case of web applications,
when you really have to keep the whole state of the view in a copy
on the server. But in a application when the controller always has
access to the view, no duplication of the view state should be
necessary. But how to solve this problem?
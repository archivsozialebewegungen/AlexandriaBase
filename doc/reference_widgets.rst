Reference widgets
~~~~~~~~~~~~~~~~~



The reference widgets constitute a plugin system to reference
documents or events. Default references are from documents to
event or vice versa or crossreferences between events.

Since the input / display of references is done by configuration,
it is necessary to implement the widgets as singletons that conform
to certain standards. Each widget consists of two components, the
view and the presenter. The view is injected into the presenter
by the dependency injection container. After injection the pesenter
makes itself known to the view, so the view may access methods
from the presenter.

The presenter does not know anything about the view execept a 
very simple interface: The view has an *items* property, that
allows the setting of the reference items (the items should have
a *__str__()* method implemented for display). And there is a 
*selected_item* property on the view that
allows to read the currently selected item.

The presenter gets also the necessary services injected and provides
methods to manipulate the reference data. The view has to use
these methods for all its data manipulating actions.
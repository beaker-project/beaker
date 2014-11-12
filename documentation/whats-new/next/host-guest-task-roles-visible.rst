Task roles are now visible between host and guest recipes
=========================================================

In previous Beaker releases, task roles were not visible between the guest 
recipes and the host recipes in a recipe set.

For example, in the following recipe set::

    <recipeSet>
      <recipe system="hostA">
        <task role="SERVERS" />
        <guestrecipe system="guest1">
          <task role="SERVERS" />
        </guestrecipe>
      </recipe>
      <recipe system="hostB">
        <task role="CLIENTS" />
        <guestrecipe system="guest2">
          <task role="CLIENTS" />
        </guestrecipe>
      </recipe>
    </recipeSet>

the role environment variables in both host recipes would have previously 
been::

    SERVERS=hostA
    CLIENTS=hostB

and in both guest recipes they would have been::

    SERVERS=guest1
    CLIENTS=guest2

However, this separation between host and guest recipes has been removed. In 
the above example, all four recipes would see the same role environment 
variables::

    SERVERS=hostA guest1
    CLIENTS=hostB guest2

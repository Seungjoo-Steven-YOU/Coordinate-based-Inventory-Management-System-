import os
import pandas as pd
import numpy as np
import json
from rapidfuzz import process, fuzz
import tkinter as tk
from tkinter import messagebox


# Make sure you have the correct files in the appropriate directories
# I will not include the directory name.
os.chdir("YOUR DIRECTORY GOES HERE")
f = open('launch.json')

f = open('launch.json')
data = json.load(f)

# Iterating through the json
# list
z_coordinate = data['z_coordinate'][0]

trans = {}
for elm in z_coordinate:
    save = z_coordinate[elm]
    trans[save] = elm

z_coordinate = trans

# Closing file
f.close()


# This is the main 'backend' class.
class UpdatedInventory:
    """
    An object that is implemented as a nested dict | list object from the two
    dataframe objects. In effect, it would combine the existing quantities of
    each product available at the store (excluding 'heavy' items like bongs
    or accessory which often does not need organization), and automatically
    sort and assign a coordinate system.

    ++++++++++++++++++ Public Attribute of class ++++++++++++++++++++++
    product_map:    dict object with product name pointing to a coordinate
    coordinate_map: dict object with coordinate pointing to a product name
    front_map:      dict object
    back_map:       dict object
    product_list:       A list object that contains all the coordinates
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    """

    def __init__(self, df, max_n=10000) -> None:
        # Create a list filled with each category specific dataframes, then we
        # can sort the values and produce a list

        # The Structure variable is a transitionary dictionary, which is close
        # to the final public attribute. The following example will illustrate
        # what the key-value map looks like:
        # - structure
        #       - Front
        #           - category 1 (maybe edible)
        #               - Product list sorted alphabetically
        #          - category 2 (maybe pre-rolls)
        #               - ...
        #           - ...
        #       - Back
        #           - category 1 (maybe edible)
        #               - Product list sorted alphabetically
        #           - category 2 (maybe pre-rolls)
        #               - ...
        #           - ...

        def categorize_and_rank(df, max_n=10000) -> dict[
            str, dict[str, list[tuple[int, str]]]]:
            """Return a nested dictionary | list. The keys are either 'F' and
            'B' for 'Front' and 'Back' and the values are the nested dictionary.
            The nested dictionary then has category names as keys and values as
            the DataFrames.

            The reason for separating the category names like this is that there
            are some categories that can not be neatly organized into one shelf.
            Even though for now, we are simply halving the category organized
            dataframes, in reality we should theoretically have *m number of
            dataframes for each category, *m being the number of unique shelves
            these objects can be placed.
            """
            result = {'F': {}, 'B': {}}
            category_list = list(df["Category Code"].unique())

            for category in category_list:
                temp = df.groupby("Category Code").get_group(category)
                temp = temp.sort_values("Rank")

                # Now each of these items should be divided nicely. For now I'm
                # going to say that half of the best sellers go in the front and
                # the other half goes in the back. THIS IS NOT HOW I WILL
                # ACTUALLY IMPLEMENT THIS, THIS IS JUST GENERAL

                temp = np.array_split(temp, 2)

                # Now transforming this temporary into a nested list with two
                # sorted lists.
                nest = []
                for thing in temp:
                    # In one line, append a list that is just the sorted
                    # Product Names
                    build_list = list(
                        thing.sort_values("Product Name")["Product Name"])
                    build_list.sort()

                    # If the build_list is bigger than it is supposed to be
                    if len(build_list) > max_n:
                        size = len(build_list)
                        idx_list = [idx + 1 for idx, val in
                                    enumerate(build_list) if val == 5]
                        build_list = [build_list[i: j] for i, j in
                                      zip([0] + idx_list, idx_list + (
                                          [size] if idx_list[
                                                        -1] != size else []))]
                    nest.append(build_list)

                for room in result:
                    # save is a dictionary; this for loop will run only twice
                    save = result[room]
                    # Now split depending on room
                    if room == 'F':
                        save[category] = nest[0]
                        result['F'] = save
                    else:
                        save[category] = nest[1]
                        result['B'] = save
            self.front_map = result["F"]
            self.back_map = result["B"]
            return result

        # Two functions to initialize the attributes
        def coordinate_map(tree: dict[str, dict[str, list[str]]]):
            """The purpose of this function is to initialize the product_map
            attribute"""
            result = {}
            for room in tree:
                # With each iteration, we should create a new coordinate
                x = room
                for category in tree[room]:
                    y = str(category)
                    products = tree[room][category]
                    for i in range(len(products)):
                        # Recall that product is
                        z = z_coordinate[i].lower()
                        coordinate = x + '.' + y + '.' + z
                        result[coordinate] = products[i]
            self.coordinate_map = result

            # initialize key_maps
            self.products_list = list(self.coordinate_map.values())
            return result

        def product_map(map_ob) -> None:
            """Literally switch the key-value pairing"""
            result = {}
            for elm in map_ob:
                save = map_ob[elm]
                result[save] = elm
            self.product_map = result

        structure = categorize_and_rank(df)
        future = coordinate_map(structure)
        product_map(future)

    def fetch(self, search: str) -> str:
        """Return the coordinate of an item when a name is typed in"""
        result = process.extractOne(search, self.products_list,
                                    scorer=fuzz.WRatio)
        name = result[0]
        return self.product_map[name]


class PageController:
    def __init__(self, root, inventory):
        self.root = root
        self.current_page = None
        self.inventory = inventory

    def navigate_to_page(self, new_page_class):
        if self.current_page:
            self.current_page.destroy()

        self.current_page = new_page_class(inventory=self.inventory,
                                           root=self.root, controller=self)
        self.current_page.show()
        print(self.current_page)
        print(type(self.root))


class StartingMenu(tk.Frame):
    """
    This StartingMenu should already have the backend loaded and ready to go,
    meaning we need the UpdatedInventory object loaded in the background.
    Ideally the methods that recall retrieving or manipulating this data should
    be done through the object methods. Otherwise, the other attributes are GUI
    specific ones.

    ============================================================================
    root: Just the tk.TK() object
    label: One label object
    entry: The search bar
    search_button: The search button
    """

    def __init__(self, inventory: UpdatedInventory,
                 controller: PageController, root) -> None:
        super().__init__(root)
        # Back end locked and loaded
        self.inventory = inventory
        self.controller = controller

        title = "NAME OF COORDINATE SYSTEM"
        self.controller.root.title(title)
        # Set geometry(width x height)
        self.controller.root.geometry('1400x700')
        self.controller.root.configure(bg='lightblue')
        self.frame = None
        self.word = ""

    def search(self, search_text) -> None:
        """Search a csv file that contains all of our current
        inventory, plus the inventory that is coming in."""
        coordinate = self.inventory.fetch(search_text)
        item = self.inventory.coordinate_map[coordinate]
        statement = "{item} is at {loc}.".format(item=item,
                                                 loc=coordinate)
        messagebox.showinfo("Search Result", statement)

    def front_move(self):
        """Move to front Room Menu"""
        # Hide the current page (StartingMenu)
        self.hide()

        # Navigate to the Backroom page
        self.controller.navigate_to_page(Frontroom)

    def back_move(self):
        """Move to Back Room Menu"""
        # Hide the current page (StartingMenu)
        self.hide()

        # Navigate to the Frontroom page
        self.controller.navigate_to_page(Backroom)

    def show(self):
        self.frame = tk.Frame(self.controller.root)
        self.frame.pack()

        # Label
        label = tk.Label(self.frame,
                         text="Search for item or check our inventory:")
        label.configure(bg='lightblue')
        label.pack(pady=80)

        # Search Entry
        entry = tk.Entry(self.frame, width=40)
        entry.pack(pady=0)

        # Search Button
        search_button = tk.Button(self.frame, text="Search",
                                  font=("Arial", 12),
                                  command=lambda: self.search(entry.get()))
        search_button.pack(pady=10)

        # Menu Screen Label
        label = tk.Label(self.frame, text="Menu Screen")
        label.pack()

        # Front Button (inside the menu screen frame)
        front = tk.Button(self.frame, text="Front", width=40, height=10,
                          font=("Arial", 12), command=self.front_move)
        front.pack(side="left", fill="both")
        front.configure(bg='orange')

        # Back Button (inside the menu screen frame)
        back = tk.Button(self.frame, text="Back", width=40, height=10,
                         font=("Arial", 12), command=self.back_move)
        back.pack(side="right", fill="both")
        back.configure(bg='orange')

    def hide(self):
        if self.frame:
            self.frame.destroy()


## COMBINE USING META CLASSES

class Frontroom(tk.Frame):
    """
    Backroom class. Should contain 3 big buttons, which will each represent
    (FOR NOW) an array with len(array) == 25 * THINK ALPHABET *
    """

    def __init__(self, inventory: UpdatedInventory, controller: PageController, root):
        super().__init__(root)
        self.controller = controller
        self.controller.root.title("Welcome to the backroom")
        self.inventory = inventory
        self.frame = None

    def show_starting_menu(self):
        self.controller.navigate_to_page(StartingMenu)
        self.hide()
        # self.controller.navigate_to_page(StartingMenu)

    def show(self):
        self.frame = tk.Frame(self.controller.root)
        self.frame.pack()

        self.label = tk.Label(self.controller.root, text="Select One")
        self.label.pack(pady=40)

        # Back Button
        self.back_button = tk.Button(self.controller.root, text="Back",
                                     command=self.show_starting_menu)
        self.back_button.pack()

    def hide(self):
        if self.frame:
            # Code to hide PageA, e.g., remove it from the GUI
            self.controller.root.destroy()


class Backroom(tk.Frame):

    def __init__(self, inventory: UpdatedInventory, controller: PageController, root):
        super().__init__(root)
        self.controller = controller
        self.controller.root.title("Welcome to the backroom")
        self.inventory = inventory
        self.frame = None

    def show_starting_menu(self):
        self.controller.navigate_to_page(StartingMenu)
        self.hide()


    def show(self):
        self.frame = tk.Frame(self.controller.root)
        self.frame.pack()

        self.label = tk.Label(self.controller.root, text="Select One")
        self.label.pack(pady=40)

        # Back Button
        self.back_button = tk.Button(self.controller.root, text="Back",
                                     command=self.show_starting_menu)
        self.back_button.pack()


    def hide(self):
        if self.frame:
            self.controller.root.destroy()


def main():
    os.chdir(r"YOUR DIRECTORY GOES HERE")
    update_inventory = pd.read_csv("update inventory.csv")
    curr = UpdatedInventory(update_inventory)
    root = tk.Tk()
    controller = PageController(root, curr)
    controller.navigate_to_page(StartingMenu)
    root.mainloop()


if __name__ == "__main__":
    main()

import os
import pandas as pd
import numpy as np
import json
from rapidfuzz import process, fuzz
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, \
    QPushButton, QVBoxLayout, QWidget, QMessageBox, QTreeView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from Testing_JSON import empty_storage
from inventoryStructure import *

################################################################################
# The objective of this program is to be able to locate and update products in
# the inventory. Currently, the main issue is a lack of a procedural method that
# everybody can follow under pressure and during a work day, with as little
# staff as possible (Tony doesn't seem to want to hire more people to do these
# shipments, but he also wants them to somehow be highly efficient like Tim and
# Jaime)

# To address this, we need to have a well established backend that maintains the
# same structure of each product and their location in an inventory with a
# functional and efficient front-end GUI application that both seasoned
# budtenders and new hires can utilize for fast item search and auditing.

# NON-PROGRAMMING IMPROVEMENTS THAT WE CAN IMPLEMENT FOR CHEAP

#   - Current ***BOX CUBBY METHOD*** is ***INEFFICIENT*** and highly
#     problematic; boxes differ in sizes, causing multiple issues such as lack
#     of standardization, inability to effectively maintain an alphabetized
#     system (as boxes can contain multiple products that get jumbled up and
#     possible 'buried'), difficulty maintaining an efficient inventory, et.

#   - Improvement in ***LIGHTING*** can help us identify package colors, see
#   'buried' items, and overall improve item retrieval for all staff.

#   - Coordinate: I will be creating a simple coordinate system. Its purpose is
#                 to allow workers to not have to find the correct 'alphabet',
#                 but instead be able to memorize the specific coordinates.
#       - An example would be instead of finding 'Good Supplies Jean Guy', which
#         can constantly change location after many shipment days, our current
#         stock, et, we would be looking for them at '1AL' (bottom,
#         Alpha, Left) or some other appropriate naming convention. If trained
#         correctly, instead of having new hires comb through alphabets, we can
#         have them immediately know the exact cubbyhole where they SHOULD be
#         located (Like your gym locker, like your high school desk, or
#         like your hotel room, at a certain point you don't even need to check
#         the unique ID of this stuff.)

#       - If used correctly, the only reason something that should be in our
#         inventory would be missing is if there was an auditing issue,
#         misplacement from budtenders, or potential theft. This is a drastic
#         improvement from what could potentially be at fault without a good
#         coordinate system, which could include the former reasons, in addition
#         to placement inconsistent with our existing sorting system, 'buried'
#         items, and being in the overstock, which makes it difficult for
#         budtenders (especially those being onboarded) to effectively clear
#         orders.

################################################################################

# This is just a dictionary for the z-coordinates from a json file.
f = open('data.json')
data = json.load(f)
map = data['z_coordinate'][0]

z_coordinate = {}

for alpha in map:
    save = map[alpha]
    z_coordinate[save] = alpha.lower()

# Closing file
f.close()

# This is the storage that is running in the background
f = open("storage.json")
obj = json.load(f)
f.close()

# The current "moves" of the store will be stored here. Detailed documentation
# of the moves will be included in the inventoryStructure.py file.
front_and_back = {"cat": 5,
                  "coordinates": ["F", "B"],
                  "columns": ["SKU", "SKU"],
                  "stable": [True, True],
                  'find': [["3.5g", "7g", "14g", "28g"], [(r"3.5g|7g",
                                                           r"14g|28g")]]}
front_flower = {'cat': 1,
                'coordinates': ["Flower 3.5g", "Flower 7g", "Flower 14g",
                                "Flower 28g", "Flower 1g", "Remainder"],
                "columns": ["Retail price", "Retail price", "Retail price",
                            "Retail price", "Retail price", "SKU"],
                'stable': [False, False, False, False, False, False],
                'find': [None, None, None, None, None, [(r'(_1x|_2x)',),
                                                        "_3x",
                                                        (r'_[4-9]x',)]]}
front_half_quarter = {'cat': 1,
                      'coordinates': ["1.2", "2.2", "3.2"],
                      "columns": "TERMINATED",
                      'stable': True}
front_prerolls = {'cat': 5,
                  'coordinates': ["4.3", "5.3", "6.3", "4.2", "Remainder"],
                  "columns": [[], [], [], [], 'Product Name'],
                  'stable': [True, True, True, True, False],
                  'find': [None, None, None, None,
                           [(":|CBD|CBG|CBN|CBC|Chocolate",)]
                           ]}
front_edibles = {'cat': 2,
                 'coordinates': ["5.2", "5.1", "Remainder"],
                 'columns': [[], [], "Product Name"],
                 'stable': [True, True, False],
                 'find': [None, None, [("Disposable|Pax",)]]
                 }
front_extracts = {'cat': 3,
                  'coordinates': ["3.3", "Cartridges"],
                  'columns': [[], "Product Name"],
                  'stable': [True, False],
                  'find': [None, [(r'0\.\d+g',)]]
                  }
front_carts = {'cat': 3,
               'coordinates': ["2.3", "1.3"],
               'columns': [[], []],
               'stable': [True, True]
               }
back_flower = {'cat': 1,
               'coordinates': ["3.2", "3.3", "Remainder"],
               "columns": ["", "", "Product Name"],
               'stable': [True, True, False],
               'find': [None, None, "Infused"]}

back_prerolls = {'cat': 5,
                 'coordinates': ["2.1", "3.1", "Remainder"],
                 "columns": [[], [], ""],
                 'stable': [True, True, False],
                 'find': [None, None, None]}
back_carts = {'cat': 3,
              'coordinates': ["2.2", "Remainder"],
              'columns': [[], "Product Name"],
              'stable': [True, False],
              'find': [None, [("Soft Chew|Gumm",)]]
              }
back_edibles = {'cat': 2,
                'coordinates': ["2.2", "TEMP"],
                'columns': [[], []],
                'stable': [True, True],
                'find': [None, None]
                }



# Main sorting_algorithm
# This is the main 'backend' class.
class UpdatedInventory:
    """
    An object that is implemented as a nested dict | list object from the two
    dataframe objects. In effect, it would combine the existing quantities of
    each product available at the store (excluding 'heavy' items like bongs
    or accessory which often does not need organization), and automatically
    sort and assign a coordinate system.

    ++++++++++++++++++ Public Attribute of class ++++++++++++++++++++++
    tree:           dict object. Consider this the master dictionary
    product_map:    dict object with product name pointing to a coordinate
    coordinate_map: dict object with coordinate pointing to a product name
    front_map:      dict object
    back_map:       dict object
    # existing_data:  bool object that is True iff the data loaded was a JSON
    ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    """

    def __init__(self, AtomicTree, max_n=10000) -> None:
        """Create a list filled with each category specific dataframes, then we
        can sort the values and produce a list

        The Structure variable is a transitionary dictionary, which is close
        to the final public attribute. The following example will illustrate
        what the key-value map looks like:
        - structure
              - Front
                  - category 1 (maybe edible)
                      - Product list sorted alphabetically
                 - category 2 (maybe pre-rolls)
                      - ...
                  - ...
              - Back
                  - category 1 (maybe edible)
                      - Product list sorted alphabetically
                  - category 2 (maybe pre-rolls)
                      - ...
                  - ..."""
        # Use empty_storage function from Testing_JSON to check if there is any
        # saved data. If there is, just load that instead of a pandas object.

        ##########################
        if not empty_storage(obj):
            # self.existing_data = True
            self.tree = obj
            update = self.coordinate_map_build(self.tree)
            self.product_map_build(update)
            print("USING JSON FILE")
        else:
            # self.existing_data = False
            structure = self.catch_and_kill(AtomicTree)
            future = self.coordinate_map_build(structure)
            self.product_map_build(future)
            print("USING CSV FILE")

    def catch_and_kill(self,
                       AtomicTree) -> dict[str, dict[str, list[tuple[int, str]]]]:
        """Initialize the front and back map, as well as the tree, then return
        the JSON file structured tree. """
        # Documentation is in inventoryStructure.py
        tree = AtomicTree.bijection()
        self.front_map = tree["F"]
        self.back_map = tree["B"]
        self.tree = tree
        return tree

    # def categorize_and_rank(self, df) -> dict[str, dict[str, list[tuple[int, str]]]]:

        # result = {'F': {}, 'B': {}}
        # category_list = list(df["Category Code"].unique())
        # for category in category_list:
        #     # The following splits a df in half based on its category and rank
        #     front_and_back = sorting_algorithm(df, "Rank",
        #                                        category, 2)
        #     for i in range(len(front_and_back)):
        #         if i == 0 and category == 1:
        #             store = sorting_algorithm(front_and_back[i],
        #                                       "Retail price",
        #                                       category, 3)
        #             # A tuple to show that it's different. Tuples will have *'s
        #             # To indicate their specialness.
        #             front_flowers = tuple(store)
        #             build_list = _step3(front_flowers)
        #         else:
        #             build_list = _step3(front_and_back[i])
        #         if i == 0:
        #             save = result["F"]
        #             save[str(category)] = build_list
        #             result["F"] = save
        #         else:
        #             save = result["B"]
        #             save[str(category)] = build_list
        #             result["B"] = save
        # self.front_map = result["F"]
        # self.back_map = result["B"]
        # self.tree = result
        # return result

    # ##########################################################################
    # Now we need to allow for a Y-coordinate to be adapted... This is
    # challenging as I have to manually code all the autistic organization styles
    # that are present in the store...Try to make the organization at least
    # somewhat logical. You might need to use classes to identify important stuff
    # Maybe use graphs to implement this program? It will have an attribute
    # which tell yous the x_coordinate (shelf) then which y_coordinate(level)
    # each item is located.
    # Or maybe use a stack with the x and y coordinates as attributes?
    # ##########################################################################

    #
    # def _coordinate_map_help(self,
    #                          front_flowers: list[list[str]]) -> tuple[str]:
    #     """
    #     THIS IS A TEMPORARY HELPER FUNCTION.
    #     For now, it's purpose is to add *'s onto the front flowers.
    #     * == "low"
    #     ** == "mid"
    #     *** == 'High'
    #     """
    #     result = []
    #
    #     for i in range(len(front_flowers)):
    #         for j in range(len(front_flowers[i])):
    #             z = z_coordinate[j].lower()
    #             addendum = '*' * (i + 1)
    #             coordinate = 'F.1.' + z + addendum
    #             data = coordinate, front_flowers[i][j]
    #             result.append(data)
    #     return result

    # Two functions to initialize the attributes
    def coordinate_map_build(self, tree: dict[str, dict[str, list[str]]]):
        """The purpose of this function is to initialize the product_map
        attribute"""
        result = {}
        for room in tree:
            for x in tree[room]:
                for y in tree[room][x]:
                    products = tree[room][x][y]
                    for i in range(len(products)):
                        z = z_coordinate[i].lower()
                        coordinate = room + '.' + x + '.' + y + '.' + z
                        result[coordinate] = products[i]

                # if isinstance(products[0], list):
                #     unique_mapping = self._coordinate_map_help(products)
                #     for front_flower in unique_mapping:
                #         coordinate, product = front_flower
                #         result[coordinate] = product
                # else:
                #     for i in range(len(products)):
                #         # Recall that product is
                #         z = z_coordinate[i].lower()
                #         coordinate = x + '.' + y + '.' + z
                #         result[coordinate] = products[i]
        self.coordinate_map = result
        # initialize key_maps
        return result

    def product_map_build(self, map_ob) -> None:
        """Literally switch the key-value pairing"""
        result = {}
        for elm in map_ob:
            save = map_ob[elm]
            result[save] = elm
        self.product_map = result

    def fetch(self, search: str) -> tuple[str]:
        """Return the coordinate of an item when a name is typed in"""
        products_list = list(self.coordinate_map.values())
        result = process.extractOne(search, products_list,
                                    scorer=fuzz.WRatio)
        name = result[0]
        coordinate = self.product_map[name]
        return self.coordinate_map[coordinate], coordinate

    def _valid_move(self, item: str, loc: str) -> bool:
        """Return True iff the item's current location is not equal to the
        moved location. For example, if an item is in the backroom, it will
        return True iff the item will be moved to the backroom

        pre-conditions: loc in ['F', 'B']
        """
        coordinate = self.fetch(item)[1]
        if coordinate[0] == loc:
            return False
        return True

    def _seek_and_destroy(self, item: str) -> None:
        """Traverse the self.tree object with the information provided in item.
        Once the item is located, remove the item. Used before the _inject
        method.
        """
        coordinate = self.fetch(item)
        # coordinate[1][0] is just the main room coordinate
        # room_stock is the front room dictionary
        room_stock = self.tree[coordinate[1][0]]
        # coordinate[1][2] is the x-coordinate. shelf_stock is the dictionary
        # at specific room and specific shelf
        shelf_stock = room_stock[coordinate[1][2]]
        # Finally, to access the bins, we must enter the correct y_coordinate.
        save = shelf_stock[coordinate[1][4]]
        # WHAT IS THE PURPOSE OF THIS??
        if not isinstance(save[0], list):
            save.remove(item)
        else:
            for elm in save:
                if item in elm:
                    elm.remove(item)

        # The shit on bottom is not necessary because the list you edited
        # carrys all changes

        # # Now the list is updated.
        # # Now update the y-coordinate
        # shelf_stock[coordinate[1][4]] = save
        # # Now update the x-coordinate
        # room_stock[coordinate[1][2]] = shelf_stock
        # # Now update the tree
        # self.tree[coordinate[1][0]] = room_stock

    # SERIOUS ISSUE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Injecting is challenging because there isn't a one-to-one coorespondence
    # in x and y coordinates

    def _inject_item(self, item: str, loc: str) -> None:
        """Inject an item into the loc, and sort accordingly."""
        coordinate = self.fetch(item)
        # Now entering the room
        room_stock = self.tree[loc]
        # Now locating x-coordinate
        shelf_stock = room_stock[coordinate[1][2]]
        # Now locating y-coordinate
        save = room_stock[coordinate[1][4]]
        # Now injecting and sorting list
        save.append(item)
        save.sort()
        # Now updating self.tree
        room_stock[coordinate[1][2]] = save
        self.tree[loc] = room_stock

    def item_to_loc(self, item: str, loc: str) -> None:
        """Move an item to a different location. After the method is executed,
        the front will include the item and re-initialize the maps
        """
        if not self._valid_move(item, loc):
            raise KeyError
        else:
            self._seek_and_destroy(item)
            self._inject_item(item, loc)
            update = self.coordinate_map_build(self.tree)
            self.product_map_build(update)


class ProductLookupApp(QMainWindow):
    def __init__(self, inventory: UpdatedInventory):
        super().__init__()
        self.inventory = inventory
        self.initUI()
        self.data_window = None
        self.inventory_layout_window = None

    def initUI(self):
        self.setWindowTitle("PACIOS")

        # Create a central widget
        central_widget = QWidget()
        # self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Create a label for the starting menu
        title = \
            "Paradise Air Coordinated Inventory Operating System (PACIOS)"
        start_label = QLabel(title)
        layout.addWidget(start_label)

        # Create a search bar
        search_label = QLabel("Enter product name:")
        layout.addWidget(search_label)

        self.search_entry1 = QLineEdit()
        layout.addWidget(self.search_entry1)

        # Create a search button
        search_button1 = QPushButton("Search")
        search_button1.clicked.connect(self.search_product)
        layout.addWidget(search_button1)

        # Create a label to display the results
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        # Have a search bar that allows you to MOVE product
        search_label = QLabel("If item must be moved, type item name:")
        layout.addWidget(search_label)

        self.search_entry2 = QLineEdit()
        layout.addWidget(self.search_entry2)

        # Create a Move button
        search_button2 = QPushButton("Move")
        search_button2.clicked.connect(self.move_item)
        layout.addWidget(search_button2)

        # Create a label to display the results
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        # Create a Data page button
        data_window_button = QPushButton("Open Data Window")
        data_window_button.clicked.connect(self.openDataWindow)
        layout.addWidget(data_window_button)

        central_widget.setLayout(layout)

        # Create a inventory layout page button
        inventory_layout_button = QPushButton("Open Inventory Layout")
        inventory_layout_button.clicked.connect(self.openLayoutWindow)
        layout.addWidget(inventory_layout_button)

        central_widget.setLayout(layout)

        # Set the central widget
        self.setCentralWidget(central_widget)

    def openDataWindow(self):
        print("DATA WINDOW ACTIVATED")
        if self.data_window is None:
            self.data_window = DataWindow(self.inventory.tree)
        self.data_window.show()
        self.hide()

    def openLayoutWindow(self):
        print("INVENTORY LAYOUT WINDOW ACTIVATED")
        if self.inventory_layout_window is None:
            page = InventoryLayoutWindow(self.inventory.tree)
            self.inventory_layout_window = page
        self.inventory_layout_window.show()

    def search_product(self):
        # Retrieve the user's input from the search bar
        search_query = self.search_entry1.text()
        # search_query = self.sender()
        name, coordinate = self.inventory.fetch(search_query)
        statement = (name +
                     " is at " + coordinate)
        self.result_label.setText(statement)

    def move_item(self):
        """Call the item_to_loc method for the class. If the operation was
        successful, there should be a pop-up that says the move was successful.
        If not, say it was unsuccessful."""
        search_query = self.search_entry2.text()
        coord = self.inventory.fetch(search_query)[1]

        # This will give you the exact name of the product
        product = self.inventory.coordinate_map[coord]

        rooms = ["F", "B"]
        for room in rooms:
            try:
                self.inventory.item_to_loc(product, room)
                break
            except KeyError:
                pass

        # The following are messages
        name, coordinate = self.inventory.fetch(search_query)
        message = name + " is now at " + coordinate
        self.result_label.setText(message)


class DataWindow(QMainWindow):
    def __init__(self, data: dict[dict[list[str]]], parent=None):
        super().__init__(parent)
        self.initUI()
        self.data = data

    def initUI(self):
        self.setWindowTitle("Data Window")
        self.setGeometry(300, 200, 400, 200)

        # Create a central widget
        central_widget = QWidget()
        # self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Create a label for the starting menu
        title = \
            "Save and close or clear all data"
        start_label = QLabel(title)
        layout.addWidget(start_label)

        # Create a button to simulate data
        self.save_button = QPushButton("Save Data and Close")
        self.save_button.clicked.connect(self.save_data_and_close)
        layout.addWidget(self.save_button)

        # Create a button to simulate data
        self.clear_button = QPushButton("Reset the inventory", self)
        self.clear_button.clicked.connect(self.showConfirmationDialog)
        layout.addWidget(self.clear_button)

        # Add the button to the layout
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def showConfirmationDialog(self):
        # Create a confirmation dialog
        confirmation = QMessageBox.question(self,
                                            'Confirmation',
                                            'Are you sure you want to proceed?',
                                            QMessageBox.Yes | QMessageBox.No)

        # Check the user's choice
        if confirmation == QMessageBox.Yes:
            self.clear_all()
            statement = 'Resetting all data. LOAD CSV FILE.'
            QMessageBox.information(self, 'Information', statement)
            self.close()
        else:
            # User clicked No, do nothing or handle accordingly
            print('User clicked No. Canceled.')

    def save_data_and_close(self):
        """After closing the application the data should be stored in the
        storage.json file"""
        try:
            with open(r"D:\My Projects\pythonProject\storage.json",
                      "w") as json_file:
                json.dump(self.data, json_file, indent=4)
        except Exception as e:
            print(f"An error occurred: {e}")

        # Close the application
        self.close()

    def clear_all(self) -> None:
        """This method should clear everything, but it would now require the csv
        file to work"""
        old = {"F": {
            "0": [],
            "1": [],
            "2": [],
            "3": [],
            "4": [],
            "5": []
        },
            "B": {
                "0": [],
                "1": [],
                "3": [],
                "4": [],
                "5": []
            }}
        try:
            with open(r"D:\My Projects\pythonProject\storage.json",
                      "w") as json_file:
                json.dump(old, json_file, indent=4)
        except Exception as e:
            print(f"An error occurred: {e}")

    def mousePressEvent(self, event):
        # Close the data window and show the starting menu when the data window
        # is clicked
        self.close()
        self.parent().show()


class InventoryLayoutWindow(QMainWindow):
    def __init__(self, data_dict: dict[dict[list[str]]], parent=None):
        super().__init__(parent)
        self.data_dict = data_dict
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Tree Visualization')
        self.setGeometry(500, 500, 400, 300)

        # Create a QTreeView widget
        self.tree_view = QTreeView(self)
        self.tree_view.setGeometry(10, 10, 380, 280)

        # Create a QStandardItemModel to represent the tree
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Tree Nodes"])

        # Create root item
        root_item = self.tree_model.invisibleRootItem()

        # Populate the tree model from the JSON dictionary
        self.populateTree(root_item, self.data_dict)

        # Set the model for the QTreeView
        self.tree_view.setModel(self.tree_model)

    def populateTree(self, parent_item, data):
        if isinstance(data, dict):
            for key, value in data.items():
                key_item = self.addTreeItem(parent_item, key)
                self.populateTree(key_item, value)
        elif isinstance(data, list):
            for item in data:
                self.populateTree(parent_item, item)
        else:
            self.addTreeItem(parent_item, str(data))

    def addTreeItem(self, parent, text):
        item = QStandardItem(text)
        parent.appendRow(item)
        return item

    def mousePressEvent(self, event):
        # Close the data window and show the starting menu when the data window
        # is clicked
        self.close()
        self.parent().show()



def main():
    app = QApplication(sys.argv)
    window = ProductLookupApp(backend)
    # window = DataWindow()
    window.show()
    sys.exit(app.exec_())


# Back end testing
if __name__ == "__main__":
    os.chdir(r"D:\My Projects\Fang Management\Inventory_Management")
    update_inventory = pd.read_csv(r"update_inventory.csv")
    update_inventory = update_inventory[update_inventory["Category Code"] != 0]
    update_inventory = update_inventory[update_inventory["Category Code"] != 4]
    # THE FOLLOWING ARE SPECIFIC TO THE ORGANIZATION STYLES OF THE OG PARADISE
    # CREW.
    atom = AtomicTree("***Main", "Rank", update_inventory,
                      main=True, find=[None])
    atom.nuke(2, **front_and_back)
    curr = atom.subtrees[0]
    curr.nuke(4, **front_flower)
    curr = curr.subtrees[0]
    curr.nuke(3, **front_half_quarter)
    curr = curr.parent.subtrees[5]
    curr.nuke(5, **front_prerolls)
    curr = curr.subtrees[4]
    curr.nuke(3, **front_edibles)
    curr = curr.subtrees[2]
    curr.nuke(2, **front_extracts)
    curr = curr.subtrees[1]
    curr.nuke(2, **front_carts)
    curr = atom.subtrees[1]
    curr.nuke(3, **back_flower)
    curr = curr.subtrees[2]
    curr.nuke(3, **back_prerolls)
    curr = curr.subtrees[2]
    curr.nuke(2, **back_carts)
    curr = curr.subtrees[1]
    curr.nuke(2, **back_edibles)
    atom.traverse_and_apply(stable_deconstruct)
    atom.bijection()
    # print(atom)
    # Now make the actual backend
    backend = UpdatedInventory(atom)
    # print(backend.front_map)
    main()

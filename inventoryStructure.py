import pandas as pd
import numpy as np
import doctest
import os
import regex as re

# Make our split dictionaries
# ###########################
# Syntax:
# [n, category, coordinates, columns, stability

pd.set_option('mode.chained_assignment', None)

# First, we split the df into Front and Backroom dfs.
# Column for Front should be SKU because we're separating 3.5's
front_and_back = {"cat": 5,
                  "coordinates": ["F", "B"],
                  "columns": ["SKU", "SKU"],
                  "stable": [True, True],
                  'find': [["3.5g", "7g", "14g", "28g"], [(r"3.5g|7g",
                                                           r"14g|28g")]]}

# Second, we divide both flowers by size (3.5, 7, 14, 28)
# p.s. I don't think we need n.. or cat lol?
front_flower = {'cat': 1,
                'coordinates': ["Flower 3.5g", "Flower 7g", "Flower 14g",
                                "Flower 28g", "Flower 1g", "Remainder"],
                "columns": ["Retail price", "Retail price", "Retail price",
                            "Retail price", "Retail price", "SKU"],
                'stable': [False, False, False, False, False, False],
                'find': [None, None, None, None, None, [(r'(_1x|_2x)',),
                                                        "_3x",
                                                        (r'_[4-9]x',)]]}
# Third, we divide the Front 3.5g flowers by retail price
front_half_quarter = {'cat': 1,
                      'coordinates': ["1.2", "2.2", "3.2"],
                      "columns": "TERMINATED",
                      'stable': True}

# Fourth, we divide pre-rolls by pack number (singles/doubles, triples, 4-10, 10+)

# IMPORTANT NOTE:
# From my understanding, the boolean split should return 6 even if we have 4
# find values. That's because boolean split will carry the remainders forward.
# WHAT ALSO MATTERS:
# What mostly matters is that the sorting algorithm return a list that is equivalent
# in size to the coordinates, columns, and stable lists. Find itself doesn't have
# to be equal size
front_prerolls = {'cat': 5,
                  'coordinates': ["4.3", "5.3", "6.3", "4.2", "Remainder"],
                  "columns": [[], [], [], [], 'Product Name'],
                  'stable': [True, True, True, True, False],
                  'find': [None, None, None, None,
                           [(":|CBD|CBG|CBN|CBC|Chocolate",)]
                           ]}

# Fifth, we divide edibles by those that are pure THC and those that are mixed
# with others (For now, this is how we'll divide the edibles)
front_edibles = {'cat': 2,
                 'coordinates': ["5.2", "5.1", "Remainder"],
                 'columns': [[], [], "Product Name"],
                 'stable': [True, True, False],
                 'find': [None, None, [("Disposable|Pax",)]]
                 }

# Sixth, we divide the vapes into dispos and carts first.
front_extracts = {'cat': 3,
                  'coordinates': ["3.3", "Cartridges"],
                  'columns': [[], "Product Name"],
                  'stable': [True, False],
                  'find': [None, [(r'0\.\d+g',)]]
                  }

# To finish up front, we divide the carts into 1g and 0.5g
front_carts = {'cat': 3,
               'coordinates': ["2.3", "1.3"],
               'columns': [[], []],
               'stable': [True, True]
               }

# Start off the back by first divvying the flowers into their respective
# weights

# We should allow the sorting algorithm to combine two or more dataframes while
# keeping them separate. Basically, I want 3.5g and 7g to be together without
# having to mix the two carelessly.
back_flower = {'cat': 1,
               'coordinates': ["3.2", "3.3", "Remainder"],
               "columns": ["", "", "Product Name"],
               'stable': [True, True, False],
               'find': [None, None, "Infused"]}

# Second, we will divvy up the pre-rolls into infused and non-infused packs
back_prerolls = {'cat': 5,
                 'coordinates': ["2.1", "3.1", "Remainder"],
                 "columns": [[], [], ""],
                 'stable': [True, True, False],
                 'find': [None, None, None]}

# Third, we will divvy up the carts. THERE SHOULD BE NO DISPOSABLES IN THE BACK
back_carts = {'cat': 3,
              'coordinates': ["2.2", "Remainder"],
              'columns': [[], "Product Name"],
              'stable': [True, False],
              'find': [None, [("Soft Chew|Gumm",)]]
              }
# ##############################################################################
# This has a lot of random crap in it that shouldn't be there... There's a few
# things in each list that is not technically 'wrong' (Like pax pods and
# dispos), but needs to be moved to different parts to more align with our
# current system...
# ##############################################################################

# Finally, we will divvy up the edibles.
# I'm saying TEMP because idk if we're gonna split it like this...
back_edibles = {'cat': 2,
                'coordinates': ["2.2", "TEMP"],
                'columns': [[], []],
                'stable': [True, True],
                'find': [None, None]
                }


class LeftOverError(Exception):
    """"""


class NotBijectiveError(Exception):
    """"""


class Node:
    """Make a basic linked list"""
    def __init__(self, cycle, tree):
        self.cycle = cycle
        self.tree = tree
        self.next = None
        self.overstock = None

    def move_item(self, product_name: str) -> None:
        """
        1. Find if product_name is in self.sorted_list. If it is not,
           raise a key error
        2. Remove that item from the list.
        3. Access the node and transition to the next tree.
        4. Inject the item and re-shuffle the list

        pre-condition: The product_name must be DIRECTLY applied to the tree of
                       interest
        Args:
            product_name: str
                The name of the product that is being moved.

        Returns: None
        """
        if product_name not in self.tree.sorted_list:
            raise ValueError
        else:
            self.tree.sorted_list.remove(product_name)
            curr = self.tree.node.next
            curr.tree.sorted_list.append(product_name)
            curr.tree.sorted_list.sort()

class LinkedCycle:
    """I'm thinking we first make LinkedLists for all the possible connections
    that are needed when an item can move front to back (potentially even
    overstock). When you click the 'move' button, it should simply find the item
    in the list that is saved in Node, delete that item, then move to the next
    node, and add that item into the new list."""
    def __init__(self, name: str, ATree, f_coord: str,
                 b_coord: str) -> None:
        """Pre-Condition: The ATree object must be the ROOT of the tree."""
        # Build a directed cycle
        self.name = name
        self.tree = ATree
        # Keep this as isolated to the trees as possible
        front = ATree.subtrees[0]
        back = ATree.subtrees[1]
        # Start with the front room. The following are trees
        front_find = front.hide_and_seek(f_coord)
        back_find = back.hide_and_seek(b_coord)
        # Create the nodes
        front_node = Node(self, front_find)
        back_node = Node(self, back_find)
        # Connect the nodes
        front_find.node = front_node
        back_find.node = back_node
        front_node.tree = front_find
        back_node.tree = back_find

        front_node.next = back_node
        back_node.next = front_node


    # def linkup(self, room, coordinate, node: Node) -> None:
    #     """Link up the front or back (Specify using room) coordinate to the
    #     correct nodes in the correct branch.
    #     """
    #     for subtree in room.subtrees:
    #         actual_coord = subtree.coordinate
    #         if actual_coord == coordinate:
    #             subtree.node = node
    #             node.tree = subtree
    #         else:
    #             self.linkup(subtree, coordinate, node)



# Main bijective higher order helper function
# curr in this case would be the current AtomicTree. An issue with the higher
# order methods was that it would end up applying methods to the original self
# rather than following the recursive function down to the leaf.
def stable_deconstruct(curr) -> None:
    """Update the self.sorted_list list. Ideally, after the trees are built,
    it snags the list and creates a separate list."""
    result = list(curr._dataframe["Product Name"])
    result.sort()
    curr.sorted_list.extend(result)


def dictionary_build(curr) -> dict[dict[list[str]]]:
    """Return a nested dictionary for each leaf."""
    result = {}
    temp = {curr.coordinate[0]: {curr.coordinate[2]: curr.sorted_list}}
    # I want to basically climb until I get to the top
    curr = curr.parent
    while not curr._stable:
        curr = curr.parent
    result[curr.coordinate] = temp
    return result

# Main dictionary creating function
def update_dict(dict1, dict2):
    for key, value2 in dict2.items():
        if key not in dict1:
            # If the key is not in dict1, add it along with its value
            dict1[key] = value2
        else:
            # If the key is in dict1, and both values are dictionaries, recursively merge them
            if isinstance(dict1[key], dict) and isinstance(value2, dict):
                update_dict(dict1[key], value2)


# Main sorting_algorithm
def sorting_algorithm(df: pd.DataFrame, category: int, column: str, n: int,
                      find=None) -> list[pd.DataFrame]:
    """Return a list of dataframes that is valid.
    """
    temp = df[df["Category Code"] == category]
    # THIS REMAINDER IS THE CATEGORY REMAINDER. IT'S A WHOLE WORLD BIGGER THAN
    # THE MORE RELEVANT 'LOCAL' REMAINDER.
    remainder = df[df["Category Code"] != category]
    if column == "":
        result = [temp]
    elif find:
        result = boolean_split(temp, column, find)
    else:
        result = sorting_split(temp, column, n)
        # Now append remainder
    if len(remainder) > 0:
        result.append(remainder)
    return result


def sorting_split(df: pd.DataFrame, column: str, n: int) -> list[pd.DataFrame]:
    """
    Return a tuple containing first the (n + 1)-sized list of DataFrame
    objects, with the remaining dataframe appended.
    First, narrow down the category.
    Then, sort by the columns. Finally, split the DataFrame.
    """
    temp = df.sort_values(column)
    # This splits it into categories
    temp = np.array_split(temp, n)
    return temp


# def boolean_help(df:pd.DataFrame, column:)

def boolean_split(df: pd.DataFrame, column: str,
                  find: str | list[str]) -> list[pd.DataFrame]:
    """
    Return an n-sized list of DataFrame objects by first narrowing down by
    going into a specified column and finding a string that matches. For example
    find disposables by setting category as "extracts inhaled" in the
    sorting_algorithm, column as "Product Name" in this function, and find as
    "disposable". Ideally, use lower method to match at all times.
    pre-condition: find == find.lower()
    """
    df["test"] = df[column].apply(lambda x: x.lower())
    df["dummy"] = False
    result = []
    new_columns = []
    if not isinstance(find, list):
        df["dummy"] = df[column].apply(lambda x: find in x)
        # That good good stuff and the remainding Ick Ick
        result = [df[df["dummy"] == 1], df[df["dummy"] == 0]]
    else:
        # I want an index that just tracks how many new columns we have

        for i in range(len(find)):
            if isinstance(find[i], tuple):
                # If there's a tuple, I want it to be a regular expression
                df[find[i]] = df[column].str.contains(find[i][0], regex=True)
                new_columns.append(find[i])
                # in_tuple is a dataframe which contains every find item that is
                # in x
                result.append(df[df[find[i]] == True])
            else:
                title = "dummy" + str(i)
                new_columns.append(title)
                df[title] = df[column].apply(lambda x: find[i] in x)
                result.append(df[df[title] == 1])
        for index, row in df.iterrows():
            values_after_11 = row.iloc[10:]
            # Basically, if any of the stuff in the list at this row is True
            # it should return 1. If not, 0.
            if sum(values_after_11) > 0:
                df.loc[index, "dummy"] = True
        # Add the remaining piece
        piece = df[df["dummy"] == False]
        result.append(piece)
        # Keep only the old columns
        clean_column = list(set(df.columns.values) - set(new_columns))
        for i in range(len(result)):
            if len(result[i]) > 0:
                result[i] = result[i][clean_column]
    return result


def simplify(**kwargs) -> tuple[bool, list[str | bool] | str | bool]:
    """Return a tuple that contains a boolean value and a list containing
    string values (like coordinate names and columns) and booleans (like
    stability). The first boolean value will be True iff the key word values
    are not lists."""
    if "find" in kwargs:
        find = kwargs["find"]
    else:
        find = None
    check = []
    for key, value in kwargs.items():
        if key not in ["cat", "coordinates"]:
            if isinstance(value, list):
                check.append(False)
            else:
                check.append(True)
    simplify = sum(check)
    coordinates = kwargs["coordinates"]
    columns = kwargs["columns"]
    stable = kwargs["stable"]
    cat = kwargs["cat"]
    result = simplify, coordinates, columns, stable, find, cat
    return result


# Consider this our main dictionary collector
dictionaries = []


class AtomicTree:
    """Tree that propagates itself using a nuke method.
    ============================================================================
    Attributes |
    ===========
    coordinate: A string value which tells you what the coordinate of the tree
    is. For the first tree, the coordinate should always be "main". For others,
    see the coordinate documentation in inventory_documentation.

    _column: A string value which tells you which column of the dataframe you
            wish to sort and split with. If self.column == "Rank" and n = 3,
            the dataframe is first sorted by rank and split into 3 dataframes.

    _category: A list value containing unique category names that are in the
               "Category Code" of self._dataframe.

    _find: A list of string values which is None iff we DON'T want to use
           boolean_split function

    _dataframe: A DataFrame object that is contained in each Atomic Tree.
               If self.dataframe == None, this is an 'exploded' dataframe.

    size: An int value which records the size of self._dataframe

    subtrees: A list of subtrees. All trees begin with an empty subtrees list.
    If len(self.subtrees) > 0, that means that the Tree has propagated.

    _main: A boolean value which is true iff this is the main root of the tree.

    _stable: A boolean value that is True iff the dataframe attribute is fully
             broken down to fit a specific coordinate. For example, sometimes
             a member of the self.subtrees group can be a remainder, which we
             will think of as being 'unstable', as in they need to undergo
             further splits. However, 'F' and 'B' are stable because they are
             not remainders but two large coordinate groups that all products
             must fit into.

    parents: Points to it's papi

    # NOTE: Include a stable attribute, which is True iff the trees are
    #       in a shelf rather than being 'processed'. For example 'F.1' is a
    #       clear coordinate.

    """

    def __init__(self, coordinate: str,
                 column: str,
                 dataframe: pd.DataFrame,
                 find=None,
                 main=False,
                 stable=True,
                 parent=None | pd.DataFrame) -> None:
        self.coordinate = coordinate
        self._column = column
        self._dataframe = dataframe
        self.size = len(self._dataframe)
        self._category = list(self._dataframe["Category Code"].unique())
        self.subtrees = []
        # Say True in the beginning
        self.main = main
        self.parent = parent
        # Say True iff we want to use boolean_split
        self._find = find
        self._stable = stable
        self.node = None
        self.sorted_list = []


    def __str__(self, level=0) -> str:
        """Return the tree structure of each of its subtrees."""
        indent = "    "
        if self._stable:
            save = str(self.coordinate) + "***"
        else:
            save = str(self.coordinate)
        tree_str = level * indent + save + "\n"
        for child in self.subtrees:
            tree_str += child.__str__(level + 1)
        return tree_str

    def __eq__(self, other) -> True:
        """Return True iff other contains an identical Dataframe
        >>> atom1 = AtomicTree("***Main", "Rank", update_inventory, main=True, find=[None])
        >>> atom2 = AtomicTree("Scooby", "doobydoo", update_inventory, main=True, find=[None])
        >>> atom1 == atom2
        True
        """
        return self._dataframe.equals(other._dataframe)

    def hide_and_seek(self, coordinate: str):
        """Return an Atomic Tree that has a matching coordinate.
        """
        for subtree in self.subtrees:
            if subtree.coordinate == coordinate:
                return subtree
            else:
                result = subtree.hide_and_seek(coordinate)
                if result is not None:
                    return result
        return None

    def _valid_nuke(self) -> bool:
        """Return True iff the sum of len(subtree._dataframes) == self._size."""
        count = 0
        for subtree in self.subtrees:
            count += subtree.size
        return count == self.size

    def nuke(self, n: int, **kwargs) -> None:
        """
        * Note: cat is there because every other split requires a category.
        1.
        2. Iterate through the categories in self._category, sort by
           self.columns, then split into n pieces
        3. If needed, concat the split dataframes. This will certainly be needed
           for the front and back room split.
        4. Iff the sum of len(subtree._dataframes) is equal to the self._size,
           this is considered a valid nuke and self._dataframe is deleted.
        Pre-Conditions:
        - len(new_coordinates) == n
        """
        # helper function to organize kwargs
        simple, coordinates, columns, stability, find, cat = simplify(**kwargs)
        if self.main:
            front = []
            back = []
            for category in self._category:
                temp = sorting_algorithm(self._dataframe,
                                         category, self._column, n)
                front.append(temp[0])
                back.append(temp[1])
            front = pd.concat(front)
            back = pd.concat(back)
            save = [front, back]
        else:
            save = sorting_algorithm(self._dataframe,
                                     cat,
                                     self._column,
                                     n,
                                     self._find)

        result = self.proliferate(save, simple, coordinates, columns, stability,
                                  find)
        # Now there are sub-atomic trees.
        self.subtrees = result
        # Test validity
        self._check()

    def proliferate(self, df_list: list[pd.DataFrame], simple: bool,
                    coordinate: list[str], columns: list[str] | str,
                    stable: list[bool] | bool, find: list[None | str]) -> list:
        """Return a list of AtomicTree based on the simple boolean value. If
        simple is True, columns and stable will be singular values."""
        result = []
        if not find:
            find = []
            for i in range(len(df_list)):
                find.append(None)
        if df_list is None:
            return []
        elif not simple:
            for i in range(len(df_list)):
                result.append(
                    AtomicTree(coordinate[i], columns[i],
                               df_list[i], stable=stable[i], parent=self,
                               find=find[i]))
        else:
            leaf = "Terminated"
            for i in range(len(df_list)):
                if i == len(df_list) - 1:
                    result.append(
                        AtomicTree(coordinate[i], columns,
                                   df_list[i], stable=stable, parent=self,
                                   find=find[i]))
                else:
                    result.append(
                        AtomicTree(coordinate[i], leaf,
                                   df_list[i], stable=True, parent=self,
                                   find=find[i]))
        return result

    def _check(self) -> None:
        if self._valid_nuke():
            pass
            # del self._dataframe
            # self._dataframe = None
        else:
            print("WHAT")
            raise LeftOverError

    # def _to_the_top(self):
    #     """
    #     Return the Main AtomicTree
    #     # >>> atom = AtomicTree("***Main", "Rank", update_inventory, main=True)
    #     # >>> atom.nuke(2, **first)
    #     # >>> curr = atom.subtrees[0]
    #     # >>> isinstance(curr._to_the_top(), AtomicTree)
    #     # True
    #     """
    #     curr = self
    #     while not curr.parent.main:
    #         curr = curr.parent
    #     return curr

    def traverse_and_apply(self, method) -> None | list[dict]:
        """Traverse the entire tree and apply class methods onto it. The two
        that I'd imagine using rn would be for stable_deconstruct and the
        bijective function."""

        if len(self.subtrees) == 0 and self._stable:  # If it's a leaf node
            output = method(self)
            if output:
                dictionaries.append(output)
        else:
            for subtree in self.subtrees:
                subtree.traverse_and_apply(method)
        return dictionaries

    def bijection(self) -> dict[dict[dict[dict[list[str]]]]]:
        """Return a nested dictionary, with the final value for each coordinate
        pairing being a list containing all the product names sorted
        alphabetically.

        pre-condition: This method will only be used AFTER stable_deconstruct
                       has been applied. Otherwise, it will have no lists to
                       retrieve, so you'll be left with a complicated nest of
                       dictionaries with no content. (ZERO MATRIX
                                                      TRANSFORMATION)
        IS THERE ANYWAY TO DO THIS RECURSIVELY???
        * It would make things way more scalable k thanks bye.
        """
        temp = self.traverse_and_apply(dictionary_build)
        for i in range(1, len(temp)):
            update_dict(temp[0], temp[i])
        return temp[0]

        # while not curr._stable:
        #     curr = curr.parent
        # if curr.coordinate not in result:
        #     # You basically want to deconstruct everything here and put it in
        #     # accordingly
        #     temp = self._dictionary_build()
        #     result[curr.coordinate] = temp
        # # If it is already there, we just need to check if the x_coordinate has
        # # not already been saved as something. If it has been, then we check
        # # y_coordinate. If they have all been taken, raise a not bijective
        # # error.
        # else:
        #     # save will be the existing temp. All we need to do is ensure
        #     # that the x_coordinates are not matching here
        #     save = result[curr.curr.coordinate]
        #     if self.coordinate[0] not in save:
        #         save[""]
        #     else:
        #         save = save[self.coordinate[0]]
        #         if self.coordinate[3] in save:
        #             raise NotBijectiveError


if __name__ == "__main__":
    os.chdir(r"D:\My Projects\Fang Management\Inventory_Management")
    update_inventory = pd.read_csv(r"update_inventory.csv")
    update_inventory = update_inventory[update_inventory["Category Code"] != 0]
    update_inventory = update_inventory[update_inventory["Category Code"] != 4]
    doctest.testmod()
    atom = AtomicTree("***Main", "Rank", update_inventory,
                      main=True, find=[None])
    atom.nuke(2, **front_and_back)
    curr = atom.subtrees[0]
    curr.nuke(4, **front_flower)
    # for i in range(len(atom.subtrees)):
    #     atom.subtrees[i].nuke(4, **second)
    # atom.subtrees[0].subtrees[]
    curr = curr.subtrees[0]
    curr.nuke(3, **front_half_quarter)
    # print(atom.subtrees[0].subtrees[4]._dataframe["Product Name"])
    # curr = curr.subtrees[4]
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
    LinkedCycle("Flowers 3.5g ", atom, "1.2", "3.1")
    # print(atom.subtrees[1].subtrees[2].subtrees[1].node)
    curr = curr.parent.parent.parent.subtrees[1]
    # print(curr.sorted_list)
    # curr = atom.subtrees[1].subtrees[2].subtrees[1]
    curr = atom.subtrees[0].subtrees[0].subtrees[0]
    print(curr.sorted_list)
    curr.node.move_item('Area 51 3.5g')
    print(curr.sorted_list)
    print(curr.node.next.tree.sorted_list)



    # print(atom.bijection())


    # print(list(curr.subtrees[1]._dataframe["Category Code"].unique()))

    # print(atom.subtrees[0])
    # print(atom.subtrees[0].subtrees[4]._dataframe["Product Name"])

    # print(curr._find)
    # print(curr.subtrees[3]._dataframe["Product Name"])

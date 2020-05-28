import pickle

# Save a dictionary into a pickle file.
favorite_color = {"lion": "yellow", "kitty": "red"}
print("\nBefore")
print(favorite_color)
file_handle = open("../data/save.p", "wb")
pickle.dump(favorite_color, file_handle)
file_handle.close()
favorite_color = {"apple": "green", "orange": "orange"}
print("\nin Between")
print(favorite_color)
file_handle = open("../data/save.p", "rb")
favorite_color = pickle.load(file_handle)
file_handle.close()
print("\nAfter:")
print(favorite_color)
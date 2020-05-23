# Import the necessary packages and modules
import matplotlib
import numpy as np
import matplotlib.pyplot as plt

# Prepare the data
x = np.linspace(0, 10, 100)

#matplotlib.use('TkAgg')

# Plot the data
plt.plot(x, x, label='linear')

# Add a legend
plt.legend()

# Show the plot
plt.show()
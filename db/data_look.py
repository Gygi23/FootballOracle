import pandas as pd

shootouts = pd.read_csv("data/raw/shootouts.csv")
print(shootouts.columns.tolist())
print(shootouts.head(3))
print(shootouts.dtypes)
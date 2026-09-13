"""Same investigator, separately frozen unchanged-source follow-up."""
from . import investigate
from .next_cases import DATA

if __name__=='__main__':
    investigate.DATA=DATA
    investigate.run()

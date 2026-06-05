import os
from scheduler import Scheduler

# Execute o programa pelo terminal: python src/main.py

def main():
    input_file = os.path.join("input", "processes.csv")
    sched = Scheduler()
    sched.load_processes_from_csv(input_file)
    sched.run()

if __name__ == "__main__":
    main()

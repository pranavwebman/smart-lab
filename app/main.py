import sys
from app.database.connection import get_engine, get_session_factory
from app.database.migrations import run_migrations
from app.ui.main_window import MainWindow

def main():
    engine = get_engine()
    session_factory = get_session_factory(engine)
    session = session_factory()

    run_migrations(session)

    app = MainWindow(session)
    app.mainloop()

if __name__ == "__main__":
    main()

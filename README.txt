STUDENT ATTENDANCE SHORTAGE ALERT SYSTEM - STARTER

Files:
- student_attendance_gui.py : Python Tkinter desktop GUI
- AttendanceBridge.java     : Java JDBC bridge to Oracle
- lib/                      : Put your existing Oracle JDBC JAR here

IMPORTANT:
1. Copy your existing ojdbc17-23.26.4.0.0.jar into this bundle's lib folder.
2. Keep both source files in the same project folder.
3. Open that folder in VS Code.
4. Run:
   python student_attendance_gui.py

The GUI compiles AttendanceBridge.java automatically when needed.
Enter your FreeSQL password in the GUI and click "Use Password".
Then enter a student roll number and subject (example: MCA105, AIP).

The Java helper calls your existing CHECK_ATTENDANCE procedure.
It does not create, modify, or delete database tables or records.

Do not share your database password or commit it to a public repository.

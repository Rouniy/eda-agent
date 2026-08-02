# Restarting the Altium MCP server through COM

See also `docs/AI_ALTIUM_FIELD_NOTES.md` for the complete AI-agent workflow,
including modal-dialog recovery, PCB focus, footprint, and ECO safety rules.

Use the script project from this repository only:

```powershell
$project = 'D:\msys64\home\Alex\src\22\eda-agent\scripts\altium\Altium_API.PrjScr'
$uri = "dxpprocess://ScriptingSystem:RunScript?ProjectName=$project|ProcName=Dispatcher.pas>StartMCPServer"
$shell = New-Object -ComObject Shell.Application
$shell.ShellExecute($uri, '', '', 'open', 0)
```

Safe reload sequence after editing Pascal sources:

1. If an Altium script-error dialog is visible, capture it and press `OK`, then
   send `Ctrl+F3` directly. Do not close the MCP status form first in this case.
2. Otherwise close the `EDA Agent MCP` status form, then send `Ctrl+F3`.
3. Run the COM snippet above and verify `application.ping`.
4. The status form starts minimized by design. Do not restore it unless its log
   is needed for diagnosis.

Do not launch scripts from `C:\Users\Alex\EDA Agent\scripts`; that legacy copy
can make Altium load units from two different checkouts.

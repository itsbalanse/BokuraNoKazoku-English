// Print function / instruction counts.
import ghidra.app.script.GhidraScript;

public class Stats extends GhidraScript {
    @Override
    public void run() throws Exception {
        println("functions=" + currentProgram.getFunctionManager().getFunctionCount()
            + " instructions=" + currentProgram.getListing().getNumInstructions());
    }
}

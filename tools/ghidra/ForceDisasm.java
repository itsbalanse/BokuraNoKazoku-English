// Force linear disassembly of the PS2 code range, create functions at jr-ra boundaries' successors,
// then re-run auto analysis so constant references (lui/addiu pairs) are discovered.
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;

public class ForceDisasm extends GhidraScript {
    @Override
    public void run() throws Exception {
        long start = 0x100000L, end = 0x29f264L;
        Listing listing = currentProgram.getListing();
        Address a = toAddr(start);
        Address e = toAddr(end);
        int n = 0;
        while (a.compareTo(e) < 0) {
            if (listing.getInstructionAt(a) == null && listing.getDefinedDataContaining(a) == null) {
                DisassembleCommand cmd = new DisassembleCommand(a, null, true);
                cmd.applyTo(currentProgram, monitor);
                n++;
            }
            Instruction ins = listing.getInstructionContaining(a);
            a = (ins != null && ins.getMaxAddress().compareTo(a) >= 0) ? ins.getMaxAddress().add(1) : a.add(4);
        }
        println("disassemble seeds: " + n + " instructions now " + listing.getNumInstructions());
        // functions: start after each "jr ra" + delay slot where no function exists
        FunctionManager fm = currentProgram.getFunctionManager();
        int created = 0;
        InstructionIterator it = listing.getInstructions(toAddr(start), true);
        boolean nextIsStart = true;
        while (it.hasNext() && !monitor.isCancelled()) {
            Instruction ins = it.next();
            if (ins.getAddress().compareTo(e) >= 0) break;
            if (nextIsStart && fm.getFunctionContaining(ins.getAddress()) == null) {
                if (createFunction(ins.getAddress(), null) != null) created++;
            }
            nextIsStart = false;
            if (ins.getMnemonicString().equals("jr") && ins.toString().contains("ra")) {
                Instruction ds = ins.getNext();
                if (ds != null) { it.next(); nextIsStart = true; }
            }
        }
        println("functions created: " + created);
        analyzeAll(currentProgram);
        println("functions=" + fm.getFunctionCount() + " instructions=" + listing.getNumInstructions());
    }
}

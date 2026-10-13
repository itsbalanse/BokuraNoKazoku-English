// Print instructions (or raw words where undecoded) for a range. Args: out start_hex count
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.*;
import java.io.*;

public class Listing extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(a[0]));
        Address p = toAddr(Long.parseLong(a[1], 16));
        int n = Integer.parseInt(a[2]);
        ghidra.program.model.listing.Listing l = currentProgram.getListing();
        Memory m = currentProgram.getMemory();
        for (int i = 0; i < n; i++) {
            Instruction ins = l.getInstructionAt(p);
            int w = m.getInt(p);
            out.println(String.format("%s  %08x  %s", p, w, ins == null ? "??" : ins.toString()));
            p = p.add(4);
        }
        out.close();
    }
}

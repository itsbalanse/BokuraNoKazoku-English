// Decompile functions that reference the given addresses, or the given function addresses.
// Args: out_file  (ref:ADDR | fn:ADDR)...
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class DecompXrefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PrintWriter out = new PrintWriter(new FileWriter(args[0]));
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        Set<Function> done = new LinkedHashSet<>();
        for (int i = 1; i < args.length; i++) {
            String a = args[i];
            List<Function> fns = new ArrayList<>();
            if (a.startsWith("ref:")) {
                Address t = toAddr(Long.parseLong(a.substring(4), 16));
                for (Reference r : getReferencesTo(t)) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    if (f == null) f = makeFn(r.getFromAddress());
                    out.println("// ref " + t + " from " + r.getFromAddress() + " in " + (f == null ? "?" : f.getName()));
                    if (f != null) fns.add(f);
                }
            } else if (a.startsWith("fn:")) {
                Address t = toAddr(Long.parseLong(a.substring(3), 16));
                Function f = getFunctionContaining(t);
                if (f == null) f = makeFn(t);
                if (f != null) fns.add(f);
            }
            for (Function f : fns) {
                if (!done.add(f)) continue;
                DecompileResults res = di.decompileFunction(f, 120, monitor);
                out.println("// ===== " + f.getName() + " @ " + f.getEntryPoint());
                out.println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "// decompile failed: " + res.getErrorMessage());
            }
        }
        out.close();
    }

    // Walk back to the closest "addiu sp,sp,-N" prologue and define a function there.
    private Function makeFn(Address from) throws Exception {
        Listing l = currentProgram.getListing();
        Address a = from;
        for (int i = 0; i < 20000; i++) {
            Instruction ins = l.getInstructionAt(a);
            if (ins != null) {
                String s = ins.toString();
                if (s.startsWith("addiu sp,sp,-")) {
                    Function f = getFunctionAt(a);
                    if (f == null) {
                        f = createFunction(a, null);
                    }
                    if (f != null && f.getBody().contains(from)) return f;
                    if (f != null) {
                        // body too short (analysis stopped); still useful
                        return f;
                    }
                }
            }
            a = a.subtract(4);
        }
        return null;
    }
}

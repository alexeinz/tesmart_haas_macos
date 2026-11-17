import SwiftUI
import TesmartKit

struct ContentView: View {
    @StateObject private var model = MatrixModel()
    @State private var preset = 1
    @State private var showNames = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            connectionBar
            Divider()
            grid
            Divider()
            actions
            Text(model.status)
                .font(.caption).foregroundStyle(.secondary)
        }
        .padding(16)
        .frame(minWidth: 760)
        .onAppear { model.startPolling() }
        .sheet(isPresented: $showNames) { NamesSheet(model: model) }
    }

    private var connectionBar: some View {
        HStack {
            TextField("Host", text: model.$host).frame(width: 150)
            TextField("Port", value: model.$port, format: .number.grouping(.never)).frame(width: 70)
            Picker("Size", selection: model.$size) {
                Text("8×8").tag(8)
                Text("16×16").tag(16)
            }.pickerStyle(.segmented).frame(width: 120)
            Button("Connect") { Task { await model.refresh() } }
            TextField("MAC filter (optional)", text: model.$macFilter).frame(width: 140)
            Button(model.scanning ? "Stop" : "Discover") { model.discover() }
            if !model.discovered.isEmpty {
                Menu("Found") {
                    ForEach(model.discovered) { d in
                        Button("\(d.host)  \(d.mac ?? "MAC unknown")  (\(d.outputs) outputs)") { model.select(d) }
                    }
                }
            }
            Toggle("Auto-refresh", isOn: $model.autoRefresh)
            if model.busy || model.scanning { ProgressView().controlSize(.small) }
        }
    }

    private func nameBinding(_ kp: ReferenceWritableKeyPath<MatrixModel, [Int: String]>, _ n: Int) -> Binding<String> {
        Binding(get: { model[keyPath: kp][n] ?? "" }, set: { model[keyPath: kp][n] = $0 })
    }

    private var grid: some View {
        ScrollView([.horizontal, .vertical]) {
            Grid(horizontalSpacing: 4, verticalSpacing: 4) {
                GridRow {
                    Text("Out ＼ In").font(.caption).frame(width: 140)
                    ForEach(1...model.size, id: \.self) { i in
                        VStack(spacing: 2) {
                            Text("\(i)").font(.caption.bold())
                            TextField("Input \(i)", text: nameBinding(\.inputNames, i))
                                .textFieldStyle(.roundedBorder).font(.caption)
                                .multilineTextAlignment(.center)
                        }.frame(width: 84)
                    }
                }
                ForEach(1...model.size, id: \.self) { o in
                    GridRow {
                        HStack(spacing: 4) {
                            Text("\(o)").font(.caption.bold()).foregroundStyle(.secondary)
                                .frame(width: 18, alignment: .trailing)
                            TextField("Out \(o)", text: nameBinding(\.outputNames, o))
                                .textFieldStyle(.roundedBorder).font(.caption)
                        }.frame(width: 140)
                        ForEach(1...model.size, id: \.self) { i in
                            cell(input: i, output: o)
                        }
                    }
                }
            }
            .padding(2)
        }
        .frame(minHeight: 260)
    }

    private func cell(input: Int, output: Int) -> some View {
        let active = model.routes[output] == input
        return Button {
            Task { await model.route(input: input, output: output) }
        } label: {
            RoundedRectangle(cornerRadius: 5)
                .fill(active ? Color.accentColor : Color.secondary.opacity(0.18))
                .frame(width: 84, height: 24)
        }
        .buttonStyle(.plain)
        .help("\(model.inputLabel(input)) → \(model.outputLabel(output))")
        .disabled(model.busy)
    }

    private var actions: some View {
        HStack(spacing: 10) {
            Menu("All outputs ←") {
                ForEach(1...model.size, id: \.self) { i in
                    Button("\(i): \(model.inputLabel(i))") { Task { await model.setAll(input: i) } }
                }
            }
            Button("Names…") { showNames = true }
            Button("Pull config…") { Task { await model.pullConfig() } }
            Button("Import…") { model.importConfig() }
            Button("Mirror") { Task { await model.mirror() } }
            Divider().frame(height: 18)
            Picker("Preset", selection: $preset) {
                ForEach(Array(TesmartProtocol.presetSlots), id: \.self) { Text("\($0)").tag($0) }
            }.frame(width: 120)
            Button("Load") { Task { await model.loadPreset(preset) } }
            Button("Save") { Task { await model.savePreset(preset) } }
            Divider().frame(height: 18)
            Toggle("Buzzer", isOn: Binding(
                get: { model.buzzer },
                set: { v in Task { await model.setBuzzer(v) } }
            ))
        }
        .disabled(model.busy)
    }
}

struct NamesSheet: View {
    @ObservedObject var model: MatrixModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 12) {
            Text("Name inputs and outputs").font(.headline)
            ScrollView {
                HStack(alignment: .top, spacing: 24) {
                    column("Inputs", \.inputNames, "Input")
                    column("Outputs", \.outputNames, "Out")
                }.padding(.horizontal, 4)
            }
            HStack {
                Button("Clear all", role: .destructive) { model.inputNames = [:]; model.outputNames = [:] }
                Spacer()
                Button("Done") { dismiss() }.keyboardShortcut(.defaultAction)
            }
        }
        .padding(16)
        .frame(width: 520, height: 460)
    }

    private func column(_ title: String, _ kp: ReferenceWritableKeyPath<MatrixModel, [Int: String]>, _ prefix: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.subheadline.bold())
            ForEach(1...model.size, id: \.self) { n in
                HStack {
                    Text("\(n)").frame(width: 24, alignment: .trailing).foregroundStyle(.secondary)
                    TextField("\(prefix) \(n)", text: Binding(
                        get: { model[keyPath: kp][n] ?? "" },
                        set: { model[keyPath: kp][n] = $0 }
                    )).textFieldStyle(.roundedBorder)
                }
            }
        }.frame(maxWidth: .infinity)
    }
}

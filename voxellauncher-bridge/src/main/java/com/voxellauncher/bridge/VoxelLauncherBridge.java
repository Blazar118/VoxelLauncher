package com.voxellauncher.bridge;

import com.sun.net.httpserver.HttpServer;
import net.fabricmc.api.ClientModInitializer;
import net.minecraft.client.MinecraftClient;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.registry.Registries;
import net.minecraft.util.Identifier;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

/**
 * VoxelLauncher Bridge - 联动 Mod 主类
 * 在 localhost:25585 启动 HTTP 服务器, 接收启动器发来的物品给予请求。
 * 启动器挖到矿石后实时发送到这里, 直接加入玩家背包。
 */
public class VoxelLauncherBridge implements ClientModInitializer {

    public static final String MOD_ID = "voxellauncher-bridge";
    public static final int PORT = 25585;
    private HttpServer server;

    @Override
    public void onInitializeClient() {
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", PORT), 0);

            // POST /give  body: {"item":"minecraft:diamond","count":16}
            server.createContext("/give", exchange -> {
                if (!"POST".equals(exchange.getRequestMethod())) {
                    sendResponse(exchange, 405, "{\"error\":\"method not allowed\"}");
                    return;
                }
                try {
                    InputStream is = exchange.getRequestBody();
                    String body = new String(is.readAllBytes(), StandardCharsets.UTF_8);
                    String itemId = extractJsonString(body, "item");
                    int count = extractJsonInt(body, "count", 1);

                    if (itemId == null || itemId.isEmpty()) {
                        sendResponse(exchange, 400, "{\"error\":\"missing item\"}");
                        return;
                    }

                    MinecraftClient mc = MinecraftClient.getInstance();
                    if (mc.player == null) {
                        sendResponse(exchange, 503, "{\"error\":\"player not in game\"}");
                        return;
                    }

                    // 解析物品 ID, 兼容带或不带 minecraft: 前缀
                    String fullId = itemId.contains(":") ? itemId : "minecraft:" + itemId;
                    Item item = Registries.ITEM.get(Identifier.of(fullId));
                    ItemStack stack = new ItemStack(item, Math.min(count, 64));

                    // 在游戏主线程执行物品添加, 避免线程安全问题
                    mc.execute(() -> {
                        try {
                            boolean inserted = mc.player.getInventory().insertStack(stack);
                            if (!inserted) {
                                mc.player.dropItem(stack, false);
                            }
                        } catch (Exception e) {
                            System.err.println("[VoxelLauncher Bridge] Failed to give item: " + e.getMessage());
                        }
                    });

                    sendResponse(exchange, 200,
                        "{\"status\":\"ok\",\"item\":\"" + fullId + "\",\"count\":" + count + "}");
                } catch (Exception e) {
                    sendResponse(exchange, 500, "{\"error\":\"" + e.getMessage() + "\"}");
                }
            });

            // GET /status 检查 Mod 是否运行
            server.createContext("/status", exchange -> {
                MinecraftClient mc = MinecraftClient.getInstance();
                boolean inGame = mc.player != null;
                sendResponse(exchange, 200,
                    "{\"mod\":\"voxellauncher-bridge\",\"version\":\"1.0.0\",\"in_game\":" + inGame + "}");
            });

            server.setExecutor(null);
            server.start();
            System.out.println("[VoxelLauncher Bridge] HTTP server started on port " + PORT);
        } catch (IOException e) {
            System.err.println("[VoxelLauncher Bridge] Failed to start server: " + e.getMessage());
        }
    }

    private void sendResponse(com.sun.net.httpserver.HttpExchange exchange, int code, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(code, bytes.length);
        OutputStream os = exchange.getResponseBody();
        os.write(bytes);
        os.close();
    }

    /** 从 JSON 字符串中提取字符串值 (简单解析, 不依赖第三方库) */
    private String extractJsonString(String json, String key) {
        String search = "\"" + key + "\":\"";
        int start = json.indexOf(search);
        if (start < 0) return null;
        start += search.length();
        int end = json.indexOf("\"", start);
        if (end < 0) return null;
        return json.substring(start, end);
    }

    /** 从 JSON 字符串中提取整数值 */
    private int extractJsonInt(String json, String key, int defaultValue) {
        String search = "\"" + key + "\":";
        int start = json.indexOf(search);
        if (start < 0) return defaultValue;
        start += search.length();
        int end = start;
        while (end < json.length() && (Character.isDigit(json.charAt(end)) || json.charAt(end) == '-')) {
            end++;
        }
        try {
            return Integer.parseInt(json.substring(start, end));
        } catch (Exception e) {
            return defaultValue;
        }
    }
}

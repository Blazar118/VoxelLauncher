package com.voxellauncher.bridge;

import com.sun.net.httpserver.HttpServer;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.MappingResolver;

import java.io.*;
import java.lang.reflect.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * VoxelLauncher Bridge - 全反射版本
 * 不直接引用任何 Minecraft 类, 通过 MappingResolver + 反射实现所有功能,
 * 直接 javac 编译即可运行, 不需要 Gradle/Loom 构建。
 */
public class VoxelLauncherBridge implements ClientModInitializer {

    public static final String MOD_ID = "voxellauncher-bridge";
    public static final int PORT = 25585;
    private HttpServer server;
    private MappingResolver resolver;

    // 缓存的类
    private Class<?> mcClass;
    private Class<?> playerClass;
    private Class<?> itemClass;
    private Class<?> itemStackClass;
    private Class<?> identifierClass;
    private Class<?> entityClass;
    private Class<?> worldClass;

    // 缓存的方法和字段
    private Method getInstanceMethod;
    private Method getPlayerMethod;
    private Method getInventoryMethod;
    private Method insertStackMethod;
    private Method dropItemMethod;
    private Method getWorldMethod;
    private Method getEntitiesMethod;
    private Method getEntityTypeMethod;
    private Method entityToStringMethod;
    private Method entityKillMethod;
    private Constructor<?> itemStackCtor;
    private Object itemRegistry;
    private Method registryGetMethod;
    private Method identifierOfMethod;

    @Override
    public void onInitializeClient() {
        try {
            resolver = FabricLoader.getInstance().getMappingResolver();
            initReflection();
            startServer();
            System.out.println("[VoxelLauncher Bridge] HTTP server started on port " + PORT + " (reflection mode)");
        } catch (Exception e) {
            System.err.println("[VoxelLauncher Bridge] Failed to initialize: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private void initReflection() throws Exception {
        // 映射类名
        mcClass = Class.forName(resolver.mapClassName("named", "net.minecraft.client.MinecraftClient"));
        playerClass = Class.forName(resolver.mapClassName("named", "net.minecraft.entity.player.PlayerEntity"));
        itemClass = Class.forName(resolver.mapClassName("named", "net.minecraft.item.Item"));
        itemStackClass = Class.forName(resolver.mapClassName("named", "net.minecraft.item.ItemStack"));
        identifierClass = Class.forName(resolver.mapClassName("named", "net.minecraft.util.Identifier"));
        entityClass = Class.forName(resolver.mapClassName("named", "net.minecraft.entity.Entity"));
        worldClass = Class.forName(resolver.mapClassName("named", "net.minecraft.world.World"));

        // MinecraftClient.getInstance() - 静态方法, 无参, 返回 MinecraftClient
        for (Method m : mcClass.getDeclaredMethods()) {
            if (Modifier.isStatic(m.getModifiers()) && m.getParameterCount() == 0 && m.getReturnType() == mcClass) {
                getInstanceMethod = m;
                getInstanceMethod.setAccessible(true);
                break;
            }
        }

        // MinecraftClient.getPlayer() - 无参, 返回 PlayerEntity 子类
        for (Method m : mcClass.getMethods()) {
            if (m.getParameterCount() == 0 && playerClass.isAssignableFrom(m.getReturnType())) {
                getPlayerMethod = m;
                break;
            }
        }

        // MinecraftClient.world 字段或方法
        for (Field f : mcClass.getFields()) {
            if (worldClass.isAssignableFrom(f.getType())) {
                getWorldMethod = null; // 用字段
                break;
            }
        }
        if (getWorldMethod == null) {
            for (Method m : mcClass.getMethods()) {
                if (m.getParameterCount() == 0 && worldClass.isAssignableFrom(m.getReturnType())) {
                    getWorldMethod = m;
                    break;
                }
            }
        }

        // PlayerEntity.getInventory() - 无参, 返回 PlayerInventory
        Class<?> invClass = Class.forName(resolver.mapClassName("named", "net.minecraft.entity.player.PlayerInventory"));
        for (Method m : playerClass.getMethods()) {
            if (m.getParameterCount() == 0 && invClass.isAssignableFrom(m.getReturnType())) {
                getInventoryMethod = m;
                break;
            }
        }

        // Inventory.insertStack(ItemStack) - 返回 boolean
        for (Method m : invClass.getMethods()) {
            if (m.getParameterCount() == 1 && m.getParameterTypes()[0] == itemStackClass && m.getReturnType() == boolean.class) {
                insertStackMethod = m;
                break;
            }
        }

        // PlayerEntity.dropItem(ItemStack, boolean) - 返回 EntityItem
        for (Method m : playerClass.getMethods()) {
            if (m.getParameterCount() == 2 && m.getParameterTypes()[0] == itemStackClass && m.getParameterTypes()[1] == boolean.class) {
                dropItemMethod = m;
                break;
            }
        }

        // ItemStack(Item, int) 构造方法
        for (Constructor<?> c : itemStackClass.getConstructors()) {
            if (c.getParameterCount() == 2 && c.getParameterTypes()[0] == itemClass && c.getParameterTypes()[1] == int.class) {
                itemStackCtor = c;
                break;
            }
        }

        // Identifier.of(String) - 静态方法
        for (Method m : identifierClass.getMethods()) {
            if (Modifier.isStatic(m.getModifiers()) && m.getParameterCount() == 1 && m.getParameterTypes()[0] == String.class && m.getReturnType() == identifierClass) {
                identifierOfMethod = m;
                break;
            }
        }

        // Registries.ITEM 注册表
        Class<?> registriesClass = Class.forName(resolver.mapClassName("named", "net.minecraft.registry.Registries"));
        Class<?> registryClass = Class.forName(resolver.mapClassName("named", "net.minecraft.registry.Registry"));
        for (Field f : registriesClass.getFields()) {
            if (registryClass.isAssignableFrom(f.getType())) {
                Object reg = f.get(null);
                // 测试这个注册表能不能通过 Identifier 获取 Item
                for (Method m : reg.getClass().getMethods()) {
                    if (m.getParameterCount() == 1 && m.getParameterTypes()[0] == identifierClass) {
                        try {
                            Object testId = identifierOfMethod.invoke(null, "minecraft:diamond");
                            Object result = m.invoke(reg, testId);
                            if (result != null && itemClass.isInstance(result)) {
                                itemRegistry = reg;
                                registryGetMethod = m;
                                break;
                            }
                        } catch (Exception ignored) {}
                    }
                }
                if (itemRegistry != null) break;
            }
        }

        // World.getEntities() - 返回 Iterable<? extends Entity>
        for (Method m : worldClass.getMethods()) {
            if (m.getParameterCount() == 0 && Iterable.class.isAssignableFrom(m.getReturnType())) {
                getEntitiesMethod = m;
                break;
            }
        }

        // Entity.getType() - 无参, 返回 EntityType
        Class<?> entityTypeClass = Class.forName(resolver.mapClassName("named", "net.minecraft.entity.EntityType"));
        for (Method m : entityClass.getMethods()) {
            if (m.getParameterCount() == 0 && entityTypeClass.isAssignableFrom(m.getReturnType())) {
                getEntityTypeMethod = m;
                break;
            }
        }

        // EntityType.toString() 或 Entity.toString() - 用于获取类型名
        // 直接用 entity.getType().toString() 或者 entity.toString()
        // 我们用 entity 的 toString, 格式通常是 "entity.minecraft.zombie['...'/...]"
        entityToStringMethod = Object.class.getMethod("toString");

        // Entity.kill() - 无参, void
        for (Method m : entityClass.getMethods()) {
            if (m.getParameterCount() == 0 && m.getReturnType() == void.class && m.getName().equals("kill")) {
                entityKillMethod = m;
                break;
            }
        }
        // 如果没找到 kill(), 找 remove() 或 setRemoved()
        if (entityKillMethod == null) {
            for (Method m : entityClass.getMethods()) {
                if (m.getParameterCount() == 0 && m.getReturnType() == void.class &&
                    (m.getName().equals("remove") || m.getName().equals("setRemoved"))) {
                    entityKillMethod = m;
                    break;
                }
            }
        }

        System.out.println("[VoxelLauncher Bridge] Reflection init complete: " +
            "mc=" + (getInstanceMethod != null) +
            ", player=" + (getPlayerMethod != null) +
            ", inv=" + (getInventoryMethod != null) +
            ", insert=" + (insertStackMethod != null) +
            ", drop=" + (dropItemMethod != null) +
            ", itemReg=" + (itemRegistry != null) +
            ", entities=" + (getEntitiesMethod != null) +
            ", kill=" + (entityKillMethod != null));
    }

    private Object getMc() throws Exception {
        return getInstanceMethod.invoke(null);
    }

    private Object getPlayer() throws Exception {
        Object mc = getMc();
        if (mc == null) return null;
        return getPlayerMethod.invoke(mc);
    }

    private Object getWorld() throws Exception {
        Object mc = getMc();
        if (mc == null) return null;
        if (getWorldMethod != null) {
            return getWorldMethod.invoke(mc);
        }
        // 用字段
        for (Field f : mcClass.getFields()) {
            if (worldClass.isAssignableFrom(f.getType())) {
                return f.get(mc);
            }
        }
        return null;
    }

    private void startServer() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", PORT), 0);

        // POST /give
        server.createContext("/give", exchange -> {
            if (!"POST".equals(exchange.getRequestMethod())) {
                sendResponse(exchange, 405, "{\"error\":\"method not allowed\"}");
                return;
            }
            try {
                String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                String itemId = extractJsonString(body, "item");
                int count = extractJsonInt(body, "count", 1);
                if (itemId == null || itemId.isEmpty()) {
                    sendResponse(exchange, 400, "{\"error\":\"missing item\"}");
                    return;
                }
                Object player = getPlayer();
                if (player == null) {
                    sendResponse(exchange, 503, "{\"error\":\"player not in game\"}");
                    return;
                }
                String fullId = itemId.contains(":") ? itemId : "minecraft:" + itemId;
                Object id = identifierOfMethod.invoke(null, fullId);
                Object item = registryGetMethod.invoke(itemRegistry, id);
                if (item == null) {
                    sendResponse(exchange, 400, "{\"error\":\"unknown item: " + fullId + "\"}");
                    return;
                }
                final Object stack = itemStackCtor.newInstance(item, Math.min(count, 64));
                final Object p = player;
                // 在游戏主线程执行
                Object mc = getMc();
                Method executeMethod = null;
                for (Method m : mcClass.getMethods()) {
                    if (m.getParameterCount() == 1 && m.getParameterTypes()[0] == Runnable.class) {
                        executeMethod = m;
                        break;
                    }
                }
                if (executeMethod != null) {
                    executeMethod.invoke(mc, (Runnable) () -> {
                        try {
                            boolean inserted = (Boolean) insertStackMethod.invoke(getInventoryMethod.invoke(p), stack);
                            if (!inserted) {
                                dropItemMethod.invoke(p, stack, false);
                            }
                        } catch (Exception e) {
                            System.err.println("[VoxelLauncher Bridge] give error: " + e.getMessage());
                        }
                    });
                } else {
                    boolean inserted = (Boolean) insertStackMethod.invoke(getInventoryMethod.invoke(p), stack);
                    if (!inserted) dropItemMethod.invoke(p, stack, false);
                }
                sendResponse(exchange, 200, "{\"status\":\"ok\",\"item\":\"" + fullId + "\",\"count\":" + count + "}");
            } catch (Exception e) {
                sendResponse(exchange, 500, "{\"error\":\"" + e.getMessage() + "\"}");
            }
        });

        // POST /kill_nearby
        server.createContext("/kill_nearby", exchange -> {
            if (!"POST".equals(exchange.getRequestMethod())) {
                sendResponse(exchange, 405, "{\"error\":\"method not allowed\"}");
                return;
            }
            try {
                String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
                String mobType = extractJsonString(body, "mob");
                int radius = extractJsonInt(body, "radius", 32);
                if (mobType == null || mobType.isEmpty()) {
                    sendResponse(exchange, 400, "{\"error\":\"missing mob type\"}");
                    return;
                }
                Object player = getPlayer();
                Object world = getWorld();
                if (player == null || world == null) {
                    sendResponse(exchange, 503, "{\"error\":\"player not in game\"}");
                    return;
                }
                final String target = mobType.toLowerCase();
                final int[] killed = {0};
                final Object w = world;
                final Object p = player;
                Object mc = getMc();
                Method executeMethod = null;
                for (Method m : mcClass.getMethods()) {
                    if (m.getParameterCount() == 1 && m.getParameterTypes()[0] == Runnable.class) {
                        executeMethod = m;
                        break;
                    }
                }
                Runnable killTask = () -> {
                    try {
                        Iterable<?> entities = (Iterable<?>) getEntitiesMethod.invoke(w);
                        for (Object e : entities) {
                            if (e == p) continue;
                            String typeName = e.toString().toLowerCase();
                            if (typeName.contains(target)) {
                                try {
                                    entityKillMethod.invoke(e);
                                    killed[0]++;
                                } catch (Exception ignored) {}
                            }
                        }
                    } catch (Exception ex) {
                        System.err.println("[VoxelLauncher Bridge] kill error: " + ex.getMessage());
                    }
                };
                if (executeMethod != null) {
                    executeMethod.invoke(mc, killTask);
                    // 等待主线程执行
                    for (int i = 0; i < 50 && killed[0] == 0; i++) {
                        Thread.sleep(10);
                    }
                } else {
                    killTask.run();
                }
                sendResponse(exchange, 200, "{\"status\":\"ok\",\"mob\":\"" + mobType + "\",\"killed\":" + killed[0] + ",\"radius\":" + radius + "}");
            } catch (Exception e) {
                sendResponse(exchange, 500, "{\"error\":\"" + e.getMessage() + "\"}");
            }
        });

        // GET /status
        server.createContext("/status", exchange -> {
            try {
                Object player = getPlayer();
                boolean inGame = player != null;
                sendResponse(exchange, 200,
                    "{\"mod\":\"voxellauncher-bridge\",\"version\":\"1.1.0-reflection\",\"in_game\":" + inGame + "}");
            } catch (Exception e) {
                sendResponse(exchange, 500, "{\"error\":\"" + e.getMessage() + "\"}");
            }
        });

        server.setExecutor(null);
        server.start();
    }

    private void sendResponse(com.sun.net.httpserver.HttpExchange exchange, int code, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(code, bytes.length);
        OutputStream os = exchange.getResponseBody();
        os.write(bytes);
        os.close();
    }

    private String extractJsonString(String json, String key) {
        String search = "\"" + key + "\":\"";
        int start = json.indexOf(search);
        if (start < 0) return null;
        start += search.length();
        int end = json.indexOf("\"", start);
        if (end < 0) return null;
        return json.substring(start, end);
    }

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

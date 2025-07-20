#!/bin/bash

# 多链钱包监控系统 - 一键启动脚本
# Multi-Chain Wallet Monitor - One-Click Setup Script

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="MultiChainWalletMonitor"
GITHUB_REPO="https://github.com/haohaoi34/jiankong"
MAIN_CLASS="com.monitor.MultiChainWalletMonitor"

# 打印标题
print_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                   多链钱包监控系统一键启动脚本                   ║"
    echo "║               Multi-Chain Wallet Monitor Setup                  ║"
    echo "║                     GitHub: haohaoi34/jiankong                   ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 打印步骤
print_step() {
    echo -e "${CYAN}[步骤] $1${NC}"
}

# 打印成功信息
print_success() {
    echo -e "${GREEN}[成功] $1${NC}"
}

# 打印警告信息
print_warning() {
    echo -e "${YELLOW}[警告] $1${NC}"
}

# 打印错误信息
print_error() {
    echo -e "${RED}[错误] $1${NC}"
}

# 打印信息
print_info() {
    echo -e "${BLUE}[信息] $1${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查Java版本
check_java() {
    print_step "检查Java环境..."
    
    if command_exists java; then
        JAVA_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}')
        JAVA_MAJOR_VERSION=$(echo $JAVA_VERSION | cut -d. -f1)
        
        if [ "$JAVA_MAJOR_VERSION" -ge 11 ]; then
            print_success "Java版本: $JAVA_VERSION (满足要求 >= 11)"
            return 0
        else
            print_warning "Java版本过低: $JAVA_VERSION，需要Java 11或更高版本"
        fi
    else
        print_warning "未检测到Java"
    fi
    
    # 尝试安装Java
    print_info "正在尝试安装Java..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install openjdk@11
            echo 'export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"' >> ~/.zshrc
            export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"
        else
            print_error "请先安装Homebrew，然后运行: brew install openjdk@11"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y openjdk-11-jdk
        elif command_exists yum; then
            sudo yum install -y java-11-openjdk-devel
        else
            print_error "无法自动安装Java，请手动安装Java 11+"
            exit 1
        fi
    else
        print_error "不支持的操作系统，请手动安装Java 11+"
        exit 1
    fi
    
    print_success "Java安装完成"
}

# 检查Maven
check_maven() {
    print_step "检查Maven环境..."
    
    if command_exists mvn; then
        MAVEN_VERSION=$(mvn -version 2>&1 | head -n 1 | awk '{print $3}')
        print_success "Maven版本: $MAVEN_VERSION"
        return 0
    else
        print_warning "未检测到Maven"
    fi
    
    # 尝试安装Maven
    print_info "正在尝试安装Maven..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install maven
        else
            print_error "请先安装Homebrew，然后运行: brew install maven"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y maven
        elif command_exists yum; then
            sudo yum install -y maven
        else
            print_error "无法自动安装Maven，请手动安装Maven 3.6+"
            exit 1
        fi
    else
        print_error "不支持的操作系统，请手动安装Maven 3.6+"
        exit 1
    fi
    
    print_success "Maven安装完成"
}

# 检查Git
check_git() {
    print_step "检查Git环境..."
    
    if command_exists git; then
        GIT_VERSION=$(git --version 2>&1 | awk '{print $3}')
        print_success "Git版本: $GIT_VERSION"
        return 0
    else
        print_warning "未检测到Git"
    fi
    
    # 尝试安装Git
    print_info "正在尝试安装Git..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install git
        else
            print_error "请先安装Homebrew，然后运行: brew install git"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            sudo apt-get update
            sudo apt-get install -y git
        elif command_exists yum; then
            sudo yum install -y git
        else
            print_error "无法自动安装Git，请手动安装Git"
            exit 1
        fi
    else
        print_error "不支持的操作系统，请手动安装Git"
        exit 1
    fi
    
    print_success "Git安装完成"
}

# 克隆项目
clone_project() {
    print_step "从GitHub获取项目..."
    
    # 获取脚本所在目录的父目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PARENT_DIR="$(dirname "$SCRIPT_DIR")"
    
    # 在父目录中创建新项目
    cd "$PARENT_DIR"
    
    # 删除已存在的目录
    if [ -d "$PROJECT_NAME" ]; then
        print_info "删除已存在的项目目录..."
        rm -rf "$PROJECT_NAME"
    fi
    
    # 克隆项目
    git clone "$GITHUB_REPO.git" "$PROJECT_NAME"
    cd "$PROJECT_NAME"
    
    print_success "项目克隆完成"
}

# 创建Maven项目结构
setup_maven_structure() {
    print_step "设置Maven项目结构..."
    
    # 创建Maven标准目录结构
    mkdir -p src/main/java/com/monitor
    mkdir -p src/main/resources
    mkdir -p src/test/java
    
    # 移动Java文件到正确位置
    if [ -f "ChainConfig.java" ]; then
        mv *.java src/main/java/com/monitor/ 2>/dev/null || true
    fi
    
    print_success "Maven项目结构创建完成"
}

# 创建pom.xml
create_pom_xml() {
    print_step "创建Maven配置文件..."
    
    cat > pom.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.monitor</groupId>
    <artifactId>multi-chain-wallet-monitor</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <name>Multi-Chain Wallet Monitor</name>
    <description>A multi-chain wallet monitoring and auto-transfer system</description>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <web3j.version>4.10.3</web3j.version>
        <okhttp.version>4.12.0</okhttp.version>
        <jackson.version>2.16.1</jackson.version>
        <slf4j.version>2.0.9</slf4j.version>
        <logback.version>1.4.14</logback.version>
        <bouncycastle.version>1.77</bouncycastle.version>
    </properties>

    <dependencies>
        <!-- Web3j for Ethereum interactions -->
        <dependency>
            <groupId>org.web3j</groupId>
            <artifactId>core</artifactId>
            <version>${web3j.version}</version>
        </dependency>

        <!-- OkHttp for HTTP requests -->
        <dependency>
            <groupId>com.squareup.okhttp3</groupId>
            <artifactId>okhttp</artifactId>
            <version>${okhttp.version}</version>
        </dependency>

        <!-- Jackson for JSON processing -->
        <dependency>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
            <version>${jackson.version}</version>
        </dependency>

        <!-- SLF4J for logging -->
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>${slf4j.version}</version>
        </dependency>

        <!-- Logback as SLF4J implementation -->
        <dependency>
            <groupId>ch.qos.logback</groupId>
            <artifactId>logback-classic</artifactId>
            <version>${logback.version}</version>
        </dependency>

        <!-- BouncyCastle for cryptography -->
        <dependency>
            <groupId>org.bouncycastle</groupId>
            <artifactId>bcprov-jdk18on</artifactId>
            <version>${bouncycastle.version}</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <!-- Maven Compiler Plugin -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>

            <!-- Maven Exec Plugin for running the application -->
            <plugin>
                <groupId>org.codehaus.mojo</groupId>
                <artifactId>exec-maven-plugin</artifactId>
                <version>3.1.0</version>
                <configuration>
                    <mainClass>com.monitor.MultiChainWalletMonitor</mainClass>
                </configuration>
            </plugin>

            <!-- Maven Shade Plugin for creating fat JAR -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-shade-plugin</artifactId>
                <version>3.4.1</version>
                <executions>
                    <execution>
                        <phase>package</phase>
                        <goals>
                            <goal>shade</goal>
                        </goals>
                        <configuration>
                            <createDependencyReducedPom>false</createDependencyReducedPom>
                            <transformers>
                                <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                                    <mainClass>com.monitor.MultiChainWalletMonitor</mainClass>
                                </transformer>
                            </transformers>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
EOF
    
    print_success "Maven配置文件创建完成"
}

# 验证Java文件
verify_java_files() {
    print_step "验证Java源文件..."
    
    REQUIRED_FILES=(
        "src/main/java/com/monitor/ChainConfig.java"
        "src/main/java/com/monitor/ConfigurationMenu.java"
        "src/main/java/com/monitor/MultiChainWalletMonitor.java"
        "src/main/java/com/monitor/TransactionSender.java"
        "src/main/java/com/monitor/WalletMonitor.java"
    )
    
    MISSING_FILES=()
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            MISSING_FILES+=("$file")
        fi
    done
    
    if [ ${#MISSING_FILES[@]} -gt 0 ]; then
        print_warning "缺少以下Java文件:"
        for file in "${MISSING_FILES[@]}"; do
            echo -e "  ${RED}- $file${NC}"
        done
        
        print_info "尝试从GitHub下载缺少的文件..."
        
        # 下载缺少的文件
        for file in "${MISSING_FILES[@]}"; do
            filename=$(basename "$file")
            print_info "下载 $filename..."
            curl -s -o "$file" "https://raw.githubusercontent.com/haohaoi34/jiankong/main/$filename"
            if [ $? -eq 0 ]; then
                print_success "下载 $filename 成功"
            else
                print_error "下载 $filename 失败"
            fi
        done
    else
        print_success "所有Java文件都存在"
    fi
}

# 编译项目
compile_project() {
    print_step "编译项目..."
    
    print_info "下载依赖并编译..."
    mvn clean compile -q
    
    if [ $? -eq 0 ]; then
        print_success "项目编译成功"
    else
        print_error "项目编译失败"
        exit 1
    fi
}

# 创建启动脚本
create_run_script() {
    print_step "创建启动脚本..."
    
    cat > run.sh << 'EOF'
#!/bin/bash

# 多链钱包监控系统启动脚本
echo "正在启动多链钱包监控系统..."
echo "如需停止程序，请按 Ctrl+C"
echo ""

# 运行程序
mvn exec:java -Dexec.mainClass="com.monitor.MultiChainWalletMonitor" -q
EOF
    
    chmod +x run.sh
    
    print_success "启动脚本创建完成"
}

# 显示使用说明
show_usage() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                        🎉 安装完成！                            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}项目位置: ${PWD}${NC}"
    echo ""
    echo -e "${CYAN}使用方法:${NC}"
    echo -e "  ${BLUE}1. 现在启动程序:${NC}"
    echo -e "     ${GREEN}./run.sh${NC}"
    echo ""
    echo -e "  ${BLUE}2. 或者使用Maven启动:${NC}"
    echo -e "     ${GREEN}mvn exec:java -Dexec.mainClass=\"com.monitor.MultiChainWalletMonitor\"${NC}"
    echo ""
    echo -e "  ${BLUE}3. 打包成JAR文件:${NC}"
    echo -e "     ${GREEN}mvn package${NC}"
    echo -e "     ${GREEN}java -jar target/multi-chain-wallet-monitor-1.0.0.jar${NC}"
    echo ""
    echo -e "${YELLOW}配置提醒:${NC}"
    echo -e "  ${RED}• 需要Alchemy API密钥 (https://www.alchemy.com/)${NC}"
    echo -e "  ${RED}• 确保钱包私钥的安全性${NC}"
    echo -e "  ${RED}• 建议先小额测试${NC}"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 检查系统依赖
    check_git
    check_java
    check_maven
    
    # 获取项目
    clone_project
    
    # 设置项目
    setup_maven_structure
    create_pom_xml
    verify_java_files
    
    # 编译项目
    compile_project
    
    # 创建启动脚本
    create_run_script
    
    # 显示使用说明
    show_usage
    
    # 询问是否立即启动
    echo ""
    read -p "是否立即启动程序? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        print_info "正在启动程序..."
        echo ""
        ./run.sh
    else
        echo ""
        print_info "你可以稍后运行 ./run.sh 来启动程序"
        echo ""
    fi
}

# 错误处理
trap 'print_error "脚本执行失败!"; exit 1' ERR

# 运行主函数
main "$@" 
